#######################################################################################
#### Utility codes and  that are called for spacewhale
#### Authors: Hieu Le & Grant Humphries
#### Date: August 2018
#######################################################################################
from __future__ import print_function, division

import os
import numpy as np
from PIL import Image
from scipy import misc
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import torchvision
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import time
import copy
import pandas as pd


class spacewhale:
    def __init__(self):
        ##### These are the data transforms used throughout the code - they are called on in other scripts
        self.data_transforms = {
            'train': transforms.Compose([
                transforms.RandomRotation(10),
                transforms.RandomResizedCrop(224),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ]),
            'val': transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ]),
            'test': transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),                
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ]),
        }

    
    def sdmkdir(self,d):
        if not os.path.isdir(d):
            os.makedirs(d)


    def savepatch_train(self,png,w,h,step,size,imbasename):

        ni = np.int32(np.floor((w- size)/step) +2)
        nj = np.int32(np.floor((h- size)/step) +2)

        for i in range(0,ni-1):
            for j in range(0,nj-1):
                name = format(i,'03d')+'_'+format(j,'03d')+'.png'
                misc.toimage(png[i*step:i*step+size,j*step:j*step+size,:]).save(imbasename+name)
        for i in range(0,ni-1):
            name = format(i,'03d')+'_'+format(nj-1,'03d')+'.png'
            misc.toimage(png[i*step:i*step+size,h-size:h,:]).save(imbasename+format(i,'03d')+'_'+format(nj-1,'03d')+'.png')


        for j in range(0,nj-1):
            name = format(ni-1,'03d')+'_'+format(j,'03d')+'.png'
            misc.toimage(png[w-size:w,j*step:j*step+size,:]).save(imbasename+format(ni-1,'03d')+'_'+format(j,'03d')+'.png')
        
        misc.toimage(png[w-size:w,h-size:h,:]).save(imbasename+format(ni-1,'03d')+'_'+format(nj-1,'03d')+'.png')




    def train_model(self, opt, device, dataset_sizes, dataloaders, model, criterion, optimizer, scheduler, num_epochs=25):
        
        since = time.time()

        for epoch in range(num_epochs):
            print('Epoch {}/{}'.format(epoch, num_epochs - 1))
            print('-' * 10)
            for phase in ['train']:
                if phase == 'train':
                    scheduler.step()
                    model.train()  # Set model to training mode
                    filename = 'epoch_'+str(epoch)+'.pth'
                else:
                    model.eval()   # Set model to evaluate mode

                running_loss = 0.0
                running_corrects = 0
                running_errors = 0

                tp=0
                tn=0
                fp=0
                fn=0

                # Iterate over data.
#                for inputs, labels  in dataloaders[phase]:
                for batch_index, (inputs, labels) in enumerate(dataloaders):
                     
                    inputs = inputs.to(device)
                    labels = labels.to(device)

                    # zero the parameter gradients
                    optimizer.zero_grad()

                    # forward
                    # track history if only in train
                    with torch.set_grad_enabled(phase == 'train'):
                        outputs = model(inputs)
                        _, preds = torch.max(outputs, 1)
                        loss = criterion(outputs, labels)

                        # backward + optimize only if in training phase
                        if phase == 'train':
                            loss.backward()
                            optimizer.step()

                    # statistics
                    running_loss += loss.item() * inputs.size(0)
                    running_corrects += torch.sum(preds == labels.data)
                    running_errors += torch.sum(preds != labels.data)

                    tp += torch.sum(preds[labels.data==0] == 0)
                    fn += torch.sum(preds[labels.data==0] == 1)
                    fp += torch.sum(preds[labels.data==1] == 0)
                    tn += torch.sum(preds[labels.data==1] ==1)


                epoch_loss = running_loss / dataset_sizes[phase]
                epoch_acc = running_corrects.double() / dataset_sizes[phase]
                epoch_err = running_errors.double() / dataset_sizes[phase]

                print('{} Loss: {:.4f} Acc: {:.4f} Err: {:.4f}'.format(
                    phase, epoch_loss, epoch_acc, epoch_err))
                torch.save(model.state_dict(),opt.checkpoint+'/'+filename)

                print('TP: {:.4f}  TN: {:.4f}  FP: {:.4f}  FN: {:.4f}'.format(tp, tn, fp, fn))

        time_elapsed = time.time() - since
        print('-----------------------------------------------------------')

        print('Training complete in {:.0f}m {:.0f}s'.format(
            time_elapsed // 60, time_elapsed % 60))
        
        print('-----------------------------------------------------------')
        
        #print('Best val Acc: {:4f}'.format(best_acc))

        # load best model weights
        #model.load_state_dict(best_model_wts)
        #return model


    def test_im(self,device,model_ft,class_names,test_transforms,im):
        A_img = Image.open(im)
        A_img = A_img.resize((224, 224),Image.NEAREST)
        A_img = test_transforms(A_img)
        A_img = torch.unsqueeze(A_img,0)
        A_img = A_img.to(device)
        pred = model_ft(A_img)
        print(pred.max())



    def test_dir(self,device,model_ft,dataloader):
        tp=0
        fp=0
        tn=0
        fn=0
        #for im, labs in dataloader:
        classified = pd.DataFrame()
        lab_list = []
        pred_list = []
        file_list = []
        for im, labs, paths in dataloader:
       

            im, labs = im.to(device), labs.to(device)        
            outputs = model_ft(im)        
            outputs = outputs
            _,preds = torch.max(outputs,1)

            ### Log the true labels, predictions, and filenames(paths) for each image
            lab_list.append(labs.data.cpu().tolist())
            pred_list.append(preds.data.cpu().tolist())
            file_list.append(paths)
            tp = tp+ torch.sum(preds[labs==0] == 0)
            fn = fn+ torch.sum(preds[labs==0] == 1)
            fp = fp +torch.sum(preds[labs==1] == 0)
            tn = tn + torch.sum(preds[labs==1] ==1)
        
        ### Write the labs, preds, and paths to csvs. Combine later and make confusion matrix in R.
        labeled = pd.DataFrame(lab_list)
        predicted = pd.DataFrame(pred_list)
        file_output = pd.DataFrame(file_list)
        labeled.to_csv('labeled.csv', index=False)
        predicted.to_csv('predicted.csv', index=False)
        file_output.to_csv('file_output.csv', index=False)
            
        ### Print out results            
        print('Correctly Identified as Water: '+ str(float(tp)))
        print('Correctly Identified as Whales: '+ str(float(tn)))
        print('Misidentified as Water: '+ str(float(fp)))    
        print('Misidentified as Whales: '+ str(float(fn)))
                        
        prec = float(tp)/float(tp+fp)
        recall =  float(tp)/ float(tp+fn)
        print("prec: %f, recall: %f"%(prec,recall))

    def make_weights_for_balanced_classes(self, images, nclasses):                        
        count = [0] * nclasses                                                      
        for item in images:                                                         
            count[item[1]] += 1                                                     
        weight_per_class = [0.] * nclasses                                      
        N = float(sum(count))                                                   
        for i in range(nclasses):                                                   
            weight_per_class[i] = N/float(count[i])                                 
        weight = [0] * len(images)                                              
        for idx, val in enumerate(images):                                          
            weight[idx] = weight_per_class[val[1]]                                  
        return weight 


class ImageFolderWithPaths(datasets.ImageFolder):
    """Custom dataset that includes image file paths. Extends
    torchvision.datasets.ImageFolder
    This adapted from Andrew Jong andrewjong/pytorch_image_folder_with_file_paths.py on github
    With this we can pull file paths from each image to line up with labels and preds later
    """

    # override the __getitem__ method. this is the method dataloader calls
    def __getitem__(self, index):
        # this is what ImageFolder normally returns 
        original_tuple = super(ImageFolderWithPaths, self).__getitem__(index)
        # the image file path
        path = self.imgs[index][0]
        # make a new tuple that includes original and the path
        tuple_with_path = (original_tuple + (path,))
        return tuple_with_path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
import torch.backends.cudnn as cudnn
import numpy as np
import torchvision
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import time
import os
from tempfile import TemporaryDirectory

if __name__ == '__main__':

    def image_show(inp, title=None):
        """Display image for Tensor."""
        inp = inp.numpy().transpose((1, 2, 0))
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        inp = std * inp + mean
        inp = np.clip(inp, 0, 1)
        plt.imshow(inp)
        if title is not None:
            plt.title(title)
        plt.pause(0.001)  # pause a bit so that plots are updated


    train_losses = []
    validation_losses = []

    train_acc = []
    validation_acc = []


    def train_model(model, criterion, optimizer, scheduler, num_epochs=25):
        since = time.time()

        # Create a temporary directory to save training checkpoints
        with TemporaryDirectory() as tempdir:
            best_model_params_path = os.path.join(tempdir, 'best_model_params.pt')

            torch.save(model.state_dict(), best_model_params_path)
            best_acc = 0.0

            for epoch in range(num_epochs):
                print(f'Epoch {epoch}/{num_epochs - 1}')
                print('-' * 10)

                # Each epoch has a training and validation phase
                for phase in ['train', 'val']:
                    if phase == 'train':
                        model.train()  # Set model to training mode
                    else:
                        model.eval()  # Set model to evaluate mode

                    running_loss = 0.0
                    running_corrects = 0

                    # Iterate over data.
                    for inputs, labels in dataloaders[phase]:
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
                    if phase == 'train':
                        scheduler.step()

                    epoch_loss = running_loss / dataset_sizes[phase]
                    epoch_acc = running_corrects.double() / dataset_sizes[phase]

                    print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

                    if phase == 'train':
                        train_losses.append(epoch_loss)
                        train_acc.append(epoch_acc.item())
                    else:
                        validation_losses.append(epoch_loss)
                        validation_acc.append(epoch_acc.item())

                    # deep copy the model
                    if phase == 'val' and epoch_acc > best_acc:
                        best_acc = epoch_acc
                        torch.save(model.state_dict(), best_model_params_path)

                print()

            time_elapsed = time.time() - since
            print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')
            print(f'Best val Acc: {best_acc:4f}')

            # load best model weights
            model.load_state_dict(torch.load(best_model_params_path))
        return model


    def validation_show(model, num_images=4):
        was_training = model.training
        model.eval()
#        images_so_far = 0
#        fig = plt.figure()

        with torch.no_grad():
            inputs, classes = next(iter(dataloaders['train']))

            outputs = torchvision.utils.make_grid(inputs)

            image_show(outputs, [class_names[x] for x in classes])

                # outputs = model(inputs)
                # _, preds = torch.max(outputs, 1)
                #
                # for j in range(inputs.size()[0]):
                #     images_so_far += 1
                #     ax = plt.subplot(num_images // 2, 2, images_so_far)
                #     ax.axis('off')
                #     ax.set_title(f'predicted: {class_names[preds[j]]}')
                #     image_show(inputs.cpu().data[j])
                #
                #     if images_so_far == num_images:
                #         model.train(mode=was_training)
                #         return
            model.train(mode=was_training)


    def plot_show(train, val, title):
        plt.title(title)
        plt.plot(train, label='train')
        plt.plot(val, label='val')
        plt.legend()
        plt.show()


    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    data_dir = 'data/dataset'

    image_datasets = {x: datasets.ImageFolder(os.path.join(data_dir, x),
                                              data_transforms[x])
                      for x in ['train', 'val']}

    dataloaders = {x: torch.utils.data.DataLoader(image_datasets[x], batch_size=4,
                                                  shuffle=True, num_workers=4)
                   for x in ['train', 'val']}

    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}

    class_names = image_datasets['train'].classes

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Get a batch of training data
    inputs, classes = next(iter(dataloaders['train']))

    # Make a grid from batch
    out = torchvision.utils.make_grid(inputs)

    image_show(out, title=[class_names[x] for x in classes])

    model_conv = models.resnet18(weights='IMAGENET1K_V1')
#    for param in model_conv.parameters():
#        param.requires_grad = False

    num_ftrs = model_conv.fc.in_features

    model_conv.fc = nn.Linear(num_ftrs, len(class_names))

    model_conv = model_conv.to(device)

    criterion = nn.CrossEntropyLoss()

    # Observe that all parameters are being optimized
    optimizer_ft = optim.SGD(model_conv.parameters(), lr=0.001, momentum=0.9)

    # Decay LR by a factor of 0.1 every 7 epochs
    exp_lr_scheduler = lr_scheduler.StepLR(optimizer_ft, step_size=7, gamma=0.1)

    model_conv = train_model(model_conv, criterion, optimizer_ft, exp_lr_scheduler,
                             num_epochs=25)

    plot_show(train_losses, validation_losses, 'losses')

    plot_show(train_acc, validation_acc, 'accuracy')

    validation_show(model_conv)
    plt.show()
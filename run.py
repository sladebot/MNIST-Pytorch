import torch.optim as optim
from torchvision import transforms
from torch.utils.data import DataLoader
import torch
import torchvision
import torch.optim as optim
from util import get_device
from torch.utils.data import DataLoader
from model import ConvNet
import torch.nn.functional as F
from box import Box
import yaml

import matplotlib.pyplot as plt
from matplotlib.pyplot import plot, draw, show, scatter, legend


class MNISTRunner:
    def __init__(self, n_epochs, batch_size_train, batch_size_test, lr, momentum=0.5):
        self.device = get_device()
        self.n_epochs = n_epochs
        self.batch_size_train = batch_size_train
        self.batch_size_test = batch_size_test
        self.transforms = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))])
        self.lr = lr
        self.momentum = momentum
        self.datapath = "data/"
        self.log_interval = 100
        train_dataset = torchvision.datasets.MNIST(root=self.datapath, train=True, transform=self.transforms, download=True)
        test_dataset = torchvision.datasets.MNIST(root=self.datapath, train=False, transform=self.transforms)

        self.train_loader = DataLoader(dataset=train_dataset, batch_size=batch_size_train, shuffle=True)
        self.test_loader = DataLoader(dataset=test_dataset, batch_size=batch_size_test, shuffle=False)

        self.model = ConvNet()
        self.model.to(self.device)

        self.optimizer = optim.SGD(self.model.parameters(), lr=self.lr,
                      momentum=self.momentum)

        self.train_losses = []
        self.train_counter = []
        self.test_losses = []
        self.test_counter = [i * len(self.train_loader.dataset) for i in range(n_epochs+1)]

    def get_example(self):
        examples = enumerate(self.test_loader)
        # batch_idx, (example_data, example_targets)
        return next(examples)

    def show_examples(self):
        _, (example_data, example_targets) = self.get_example()
        fig = plt.figure()
        for i in range(6):
            plt.subplot(2,3,i+1)
            plt.tight_layout()
            plt.imshow(example_data[i][0], cmap='gray', interpolation='none')
            plt.title("Ground Truth: {}".format(example_targets[i]))
            plt.xticks([])
            plt.yticks([])
        fig

    def train_mode(self):
        self.model.train()

    def train(self, epoch):
        self.model.train()
        for batch_idx, (data, target) in enumerate(self.train_loader):
            data = data.to(self.device)
            target = target.to(self.device)
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = F.nll_loss(output, target)
            loss.backward()
            self.optimizer.step()
            if batch_idx % self.log_interval == 0:
                print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                    epoch, batch_idx * len(data), len(self.train_loader.dataset),
                           100. * batch_idx / len(self.train_loader), loss.item()))
                self.train_losses.append(loss.item())
                self.train_counter.append(
                    (batch_idx * 64) + ((epoch - 1) * len(self.train_loader.dataset)))
        self.test()
        self.save_model(self.model, self.optimizer, model_name="mnist")

    def resume_training(self, min, max):
        model = ConvNet()
        model = model.to(self.device)
        model_state_dict = torch.load(f"{self.datapath}/model.pth")
        model.load_state_dict(model_state_dict)
        model.train()
        self.model = model
        optimizer_state_dict = torch.load(f"{self.datapath}/optimizer.pth")
        optimizer = optim.SGD(self.model.parameters(), lr=self.lr,
                      momentum=self.momentum)
        optimizer.load_state_dict(optimizer_state_dict)
        self.optimizer = optimizer

        for i in range(min, max):
            self.train(i)

    def draw_chart(self):
        plot(self.train_counter, self.train_losses, label="Train Loss", color='blue')
        scatter(self.test_counter, self.test_losses, label="Test Loss", color='red', marker='o')
        legend()
        show()

    def test(self):
        self.model.eval()
        test_loss = 0
        correct = 0
        with torch.no_grad():
            for data, target in self.test_loader:
                data = data.to(self.device)
                target = target.to(self.device)
                output = self.model(data)
                test_loss += F.nll_loss(output, target, size_average=False).item()
                pred = output.data.max(1, keepdim=True)[1]
                correct += pred.eq(target.data.view_as(pred)).sum()
        test_loss /= len(self.test_loader.dataset)
        self.test_losses.append(test_loss)
        print('\nTest set: Avg. loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
            test_loss, correct, len(self.test_loader.dataset),
            100. * correct / len(self.test_loader.dataset)))

    def save_model(self, model, optimizer, model_name="model"):
        torch.save(model.state_dict(), f"{self.datapath}/{model_name}.pth")
        torch.save(optimizer.state_dict(), f"{self.datapath}/optimizer.pth")


def get_config(path="./config.yaml"):
    with open(path, 'r') as f:
        try:
            config = Box(yaml.safe_load(f))
        except yaml.YAMLError as exc:
            print(exc)
    return config


def train(cfg):
    runner = MNISTRunner(
        n_epochs=cfg.n_epochs,
        batch_size_train=cfg.batch_size_train,
        batch_size_test=cfg.batch_size_test,
        lr=cfg.lr)
    n_epochs = cfg.n_epochs
    # runner.show_examples()
    runner.test()
    for epoch in range(1, n_epochs+1):
        runner.train(epoch)
    runner.draw_chart()


def resume(cfg):
    runner = MNISTRunner(
        n_epochs=cfg.n_epochs,
        batch_size_train=cfg.batch_size_train,
        batch_size_test=cfg.batch_size_test,
        lr=cfg.lr)

    runner.resume_training(min=4, max=9)


if __name__ == "__main__":
    cfg = get_config()
    train(cfg)
    # resume(cfg)

import torch
import torch.nn as nn
import utils.network as net_utils

from layers.reorg.reorg_layer import ReorgLayer


def _make_layers(in_channels, cfg):
    layers = []

    if len(cfg) > 0 and isinstance(cfg[0], list):
        for sub_cfg in cfg:
            layer, in_channels = _make_layers(in_channels, sub_cfg)
            layers.append(layer)

    for item in cfg:
        if item == 'M':
            layers.append(nn.MaxPool2d(kernel_size=2, stride=2))
        else:
            out_channels, ksize = item
            layers.append(net_utils.Conv2d_BatchNorm(in_channels, out_channels, ksize, same_padding=True))
            in_channels = out_channels

    return nn.Sequential(*layers), in_channels


class Darknet19(nn.Module):
    def __init__(self):
        super(Darknet19, self).__init__()

        cfgs = [
            # conv1s
            [(32, 3)],
            ['M', (64, 3)],
            ['M', (128, 3), (64, 1), (128, 3)],
            ['M', (256, 3), (128, 1), (256, 3)],
            ['M', (512, 3), (256, 1), (512, 3), (256, 1), (512, 3)],
            # conv2
            ['M', (1024, 3), (512, 1), (1024, 3), (512, 1), (1024, 3)],
            # ------------
            # conv3
            [(1024, 3), (1024, 3)],
            # conv4
            [(1024, 3)]
        ]

        # darknet
        self.conv1s, c1 = _make_layers(3, cfgs[0:5])
        self.conv2, c2 = _make_layers(c1, cfgs[5])
        # ---
        self.conv3, c3 = _make_layers(c2, cfgs[6])

        stride = 2
        self.reorg = ReorgLayer(stride=2)   # stride*stride times the channels of conv1s
        # cat [conv1s, conv3]
        self.conv4, c4 = _make_layers((c1*(stride*stride) + c3), cfgs[7])

        # linear
        self.conv5 = net_utils.Conv2d(c4, 125, 1, 1, relu=False)

    def forward(self, im_data):
        conv1s = self.conv1s(im_data)
        conv2 = self.conv2(conv1s)

        conv3 = self.conv3(conv2)

        conv1s_reorg = self.reorg(conv1s)
        cat_1_3 = torch.cat([conv1s_reorg, conv3], dimension=1)

        conv4 = self.conv4(cat_1_3)
        conv5 = self.conv5(conv4)

        return conv5





import os
import numpy as np
import torch
import collections
import random
from tqdm import tqdm

def moving_average(a, window_size):
    cumulative_sum = np.cumsum(np.insert(a, 0, 0))
    middle = (cumulative_sum[window_size:] - cumulative_sum[:-window_size]) / window_size
    r = np.arange(1, window_size - 1, 2)
    begin = np.cumsum(a[:window_size - 1])[::2] / r
    end = (np.cumsum(a[:-window_size:-1]) / r)[::-1]
    return np.concatenate((begin, middle, end))
    
def window_average(a, window_size):
    res = []
    for i in range(len(a)):
        if i < window_size:
            res.append(np.mean(a[:i+1]))
        elif i > len(a) - window_size:
            res.append(np.mean(a[i:]))
        else:
            res.append(np.mean(a[i-window_size+1:i+1]))
    return res
        

def compute_advantage(gamma, lmbda, td_delta):
    
    td_delta = td_delta.detach().numpy()
    advantage_list = []
    advantage = 0.0
    for delta in td_delta[::-1]:
        advantage = gamma * lmbda * advantage + delta
        advantage_list.append(advantage)
    advantage_list.reverse()
    return torch.tensor(advantage_list, dtype=torch.float)
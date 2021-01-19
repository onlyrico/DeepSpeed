'''
Copyright 2020 The Microsoft DeepSpeed Team
'''

import torch.nn.init as init
import torch
import torch.distributed as dist

# import for sanity testing only
#from .basic_moe import BasicMoE

from .sharded_moe import ShardedMoE
from .experts import Experts
import copy 

class MoE(torch.nn.Module):
    '''
        DeepSpeed MOE API: This defines a simple API that can be used from client-side code.
        E.g. See more details of usage from Megatron-LM code in https://github.com/microsoft/DeepSpeedExamples/tree/amawa/moe
    '''
    def __init__(self, hidden_size, output_dropout_prob, expert, num_experts=1): 
        super(MoE, self).__init__()
        
        num_experts = num_experts // dist.get_world_size()

        self.experts = Experts(expert, num_experts) 
        
        self.moe = ShardedMoE(
                        hidden_size,
                        num_experts=num_experts,
                        second_policy_train = 'random', # in top_2 gating, policy for whether to use a second-place expert
                        second_policy_eval = 'random',  # all (always) | none (never) | threshold (if gate value > the given threshold) | random (if gate value > threshold * random_uniform(0, 1))
                        second_threshold_train = 0.2,
                        second_threshold_eval = 0.2,
                        capacity_factor_train = 1.25,   # experts have fixed capacity per batch. we need some extra capacity in case gating is not perfectly balanced.
                        capacity_factor_eval = 2.,      # capacity_factor_* should be set to a value >=1
                        loss_coef = 1e-2,               # multiplier on the auxiliary expert balancing auxiliary loss
                        experts=self.experts)

        self.dropout = torch.nn.Dropout(output_dropout_prob)

    def forward(self, hidden_states):
        output, loss = self.moe(hidden_states)
        output = self.dropout(output)
        return output, loss

from transformers import Qwen2Config

from tokasaurus.model.llama import (
    LlamaAttention,
    LlamaBlock,
    LlamaForCausalLM,
    LlamaModel,
)


class Qwen2Attention(LlamaAttention):
    qkv_bias: bool = True


class Qwen2Block(LlamaBlock):
    attn_cls = Qwen2Attention


class Qwen2Model(LlamaModel):
    block_cls = Qwen2Block


class Qwen2ForCausalLM(LlamaForCausalLM):
    model_cls = Qwen2Model
    config_cls = Qwen2Config

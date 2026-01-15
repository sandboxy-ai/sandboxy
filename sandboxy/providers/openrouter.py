"""OpenRouter provider - unified API for 400+ models."""

import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)

from sandboxy.providers.base import BaseProvider, ModelInfo, ModelResponse, ProviderError

# Popular models with their metadata (subset - OpenRouter has 400+)
OPENROUTER_MODELS = {
    # ==========================================================================
    # OpenAI (Latest: GPT-5.x series)
    # ==========================================================================
    "openai/gpt-5.2-pro": ModelInfo(
        id="openai/gpt-5.2-pro",
        name="GPT-5.2 Pro",
        provider="openai",
        context_length=400000,
        input_cost_per_million=21.00,
        output_cost_per_million=168.00,
        supports_vision=True,
    ),
    "openai/gpt-5.2": ModelInfo(
        id="openai/gpt-5.2",
        name="GPT-5.2",
        provider="openai",
        context_length=400000,
        input_cost_per_million=1.75,
        output_cost_per_million=14.00,
        supports_vision=True,
    ),
    "openai/gpt-5.2-codex": ModelInfo(
        id="openai/gpt-5.2-codex",
        name="GPT-5.2 Codex",
        provider="openai",
        context_length=400000,
        input_cost_per_million=1.75,
        output_cost_per_million=14.00,
        supports_vision=True,
    ),
    "openai/gpt-5-mini": ModelInfo(
        id="openai/gpt-5-mini",
        name="GPT-5 Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=0.30,
        output_cost_per_million=2.40,
        supports_vision=True,
    ),
    "openai/gpt-5.1": ModelInfo(
        id="openai/gpt-5.1",
        name="GPT-5.1",
        provider="openai",
        context_length=400000,
        input_cost_per_million=1.25,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "openai/gpt-5.1-codex": ModelInfo(
        id="openai/gpt-5.1-codex",
        name="GPT-5.1 Codex",
        provider="openai",
        context_length=400000,
        input_cost_per_million=0.30,
        output_cost_per_million=2.40,
        supports_vision=True,
    ),
    "openai/gpt-4.1": ModelInfo(
        id="openai/gpt-4.1",
        name="GPT-4.1",
        provider="openai",
        context_length=1000000,
        input_cost_per_million=2.00,
        output_cost_per_million=8.00,
        supports_vision=True,
    ),
    "openai/gpt-4.1-mini": ModelInfo(
        id="openai/gpt-4.1-mini",
        name="GPT-4.1 Mini",
        provider="openai",
        context_length=1000000,
        input_cost_per_million=0.40,
        output_cost_per_million=1.60,
        supports_vision=True,
    ),
    "openai/gpt-4.1-nano": ModelInfo(
        id="openai/gpt-4.1-nano",
        name="GPT-4.1 Nano",
        provider="openai",
        context_length=1000000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.40,
        supports_vision=True,
    ),
    "openai/gpt-4o": ModelInfo(
        id="openai/gpt-4o",
        name="GPT-4o",
        provider="openai",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "openai/gpt-4o-mini": ModelInfo(
        id="openai/gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        supports_vision=True,
    ),
    "openai/o3": ModelInfo(
        id="openai/o3",
        name="o3",
        provider="openai",
        context_length=200000,
        input_cost_per_million=20.00,
        output_cost_per_million=80.00,
    ),
    "openai/o3-mini": ModelInfo(
        id="openai/o3-mini",
        name="o3 Mini",
        provider="openai",
        context_length=200000,
        input_cost_per_million=1.10,
        output_cost_per_million=4.40,
    ),
    "openai/o1": ModelInfo(
        id="openai/o1",
        name="o1",
        provider="openai",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=60.00,
    ),
    "openai/o1-mini": ModelInfo(
        id="openai/o1-mini",
        name="o1 Mini",
        provider="openai",
        context_length=128000,
        input_cost_per_million=3.00,
        output_cost_per_million=12.00,
    ),
    "openai/o1-pro": ModelInfo(
        id="openai/o1-pro",
        name="o1 Pro",
        provider="openai",
        context_length=200000,
        input_cost_per_million=150.00,
        output_cost_per_million=600.00,
    ),
    # ==========================================================================
    # Anthropic (Latest: Claude 4.5 series)
    # ==========================================================================
    "anthropic/claude-opus-4.5": ModelInfo(
        id="anthropic/claude-opus-4.5",
        name="Claude Opus 4.5",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=5.00,
        output_cost_per_million=25.00,
        supports_vision=True,
    ),
    "anthropic/claude-sonnet-4.5": ModelInfo(
        id="anthropic/claude-sonnet-4.5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        context_length=1000000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "anthropic/claude-haiku-4.5": ModelInfo(
        id="anthropic/claude-haiku-4.5",
        name="Claude Haiku 4.5",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=1.00,
        output_cost_per_million=5.00,
        supports_vision=True,
    ),
    "anthropic/claude-sonnet-4": ModelInfo(
        id="anthropic/claude-sonnet-4",
        name="Claude Sonnet 4",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "anthropic/claude-opus-4": ModelInfo(
        id="anthropic/claude-opus-4",
        name="Claude Opus 4",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    "anthropic/claude-3.5-sonnet": ModelInfo(
        id="anthropic/claude-3.5-sonnet",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "anthropic/claude-3.5-haiku": ModelInfo(
        id="anthropic/claude-3.5-haiku",
        name="Claude 3.5 Haiku",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.80,
        output_cost_per_million=4.00,
        supports_vision=True,
    ),
    "anthropic/claude-3-opus": ModelInfo(
        id="anthropic/claude-3-opus",
        name="Claude 3 Opus",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=15.00,
        output_cost_per_million=75.00,
        supports_vision=True,
    ),
    "anthropic/claude-3-haiku": ModelInfo(
        id="anthropic/claude-3-haiku",
        name="Claude 3 Haiku",
        provider="anthropic",
        context_length=200000,
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        supports_vision=True,
    ),
    # ==========================================================================
    # Google (Latest: Gemini 3.x series)
    # ==========================================================================
    "google/gemini-3-pro": ModelInfo(
        id="google/gemini-3-pro",
        name="Gemini 3 Pro",
        provider="google",
        context_length=1048576,
        input_cost_per_million=2.00,
        output_cost_per_million=12.00,
        supports_vision=True,
    ),
    "google/gemini-3-flash": ModelInfo(
        id="google/gemini-3-flash",
        name="Gemini 3 Flash",
        provider="google",
        context_length=1048576,
        input_cost_per_million=0.30,
        output_cost_per_million=1.20,
        supports_vision=True,
    ),
    "google/gemini-2.5-pro": ModelInfo(
        id="google/gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="google",
        context_length=1048576,
        input_cost_per_million=1.25,
        output_cost_per_million=10.00,
        supports_vision=True,
    ),
    "google/gemini-2.5-flash": ModelInfo(
        id="google/gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="google",
        context_length=1048576,
        input_cost_per_million=0.30,
        output_cost_per_million=2.50,
        supports_vision=True,
    ),
    "google/gemini-2.0-flash": ModelInfo(
        id="google/gemini-2.0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.40,
        supports_vision=True,
    ),
    "google/gemini-2.0-flash-exp:free": ModelInfo(
        id="google/gemini-2.0-flash-exp:free",
        name="Gemini 2.0 Flash (Free)",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        supports_vision=True,
    ),
    "google/gemini-2.0-flash-thinking-exp:free": ModelInfo(
        id="google/gemini-2.0-flash-thinking-exp:free",
        name="Gemini 2.0 Flash Thinking (Free)",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        supports_vision=True,
    ),
    "google/gemini-pro-1.5": ModelInfo(
        id="google/gemini-pro-1.5",
        name="Gemini Pro 1.5",
        provider="google",
        context_length=2000000,
        input_cost_per_million=1.25,
        output_cost_per_million=5.00,
        supports_vision=True,
    ),
    "google/gemini-flash-1.5": ModelInfo(
        id="google/gemini-flash-1.5",
        name="Gemini Flash 1.5",
        provider="google",
        context_length=1000000,
        input_cost_per_million=0.075,
        output_cost_per_million=0.30,
        supports_vision=True,
    ),
    # ==========================================================================
    # xAI (Latest: Grok 4)
    # ==========================================================================
    "x-ai/grok-4": ModelInfo(
        id="x-ai/grok-4",
        name="Grok 4",
        provider="xai",
        context_length=2000000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_vision=True,
    ),
    "x-ai/grok-4-fast": ModelInfo(
        id="x-ai/grok-4-fast",
        name="Grok 4 Fast",
        provider="xai",
        context_length=2000000,
        input_cost_per_million=0.20,
        output_cost_per_million=0.50,
        supports_vision=True,
    ),
    "x-ai/grok-3": ModelInfo(
        id="x-ai/grok-3",
        name="Grok 3",
        provider="xai",
        context_length=131072,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
    ),
    "x-ai/grok-3-mini": ModelInfo(
        id="x-ai/grok-3-mini",
        name="Grok 3 Mini",
        provider="xai",
        context_length=131072,
        input_cost_per_million=0.30,
        output_cost_per_million=0.50,
    ),
    # ==========================================================================
    # DeepSeek
    # ==========================================================================
    "deepseek/deepseek-chat": ModelInfo(
        id="deepseek/deepseek-chat",
        name="DeepSeek V3",
        provider="deepseek",
        context_length=64000,
        input_cost_per_million=0.14,
        output_cost_per_million=0.28,
    ),
    "deepseek/deepseek-r1": ModelInfo(
        id="deepseek/deepseek-r1",
        name="DeepSeek R1",
        provider="deepseek",
        context_length=64000,
        input_cost_per_million=0.55,
        output_cost_per_million=2.19,
    ),
    "deepseek/deepseek-r1-distill-llama-70b": ModelInfo(
        id="deepseek/deepseek-r1-distill-llama-70b",
        name="DeepSeek R1 Distill Llama 70B",
        provider="deepseek",
        context_length=128000,
        input_cost_per_million=0.23,
        output_cost_per_million=0.69,
    ),
    "deepseek/deepseek-r1-distill-qwen-32b": ModelInfo(
        id="deepseek/deepseek-r1-distill-qwen-32b",
        name="DeepSeek R1 Distill Qwen 32B",
        provider="deepseek",
        context_length=128000,
        input_cost_per_million=0.14,
        output_cost_per_million=0.28,
    ),
    "deepseek/deepseek-r1:free": ModelInfo(
        id="deepseek/deepseek-r1:free",
        name="DeepSeek R1 (Free)",
        provider="deepseek",
        context_length=64000,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
    ),
    # ==========================================================================
    # Meta (Llama)
    # ==========================================================================
    "meta-llama/llama-3.3-70b-instruct": ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct",
        name="Llama 3.3 70B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.12,
        output_cost_per_million=0.30,
    ),
    "meta-llama/llama-3.3-70b-instruct:free": ModelInfo(
        id="meta-llama/llama-3.3-70b-instruct:free",
        name="Llama 3.3 70B (Free)",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
    ),
    "meta-llama/llama-3.1-405b-instruct": ModelInfo(
        id="meta-llama/llama-3.1-405b-instruct",
        name="Llama 3.1 405B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=2.00,
        output_cost_per_million=2.00,
    ),
    "meta-llama/llama-3.1-70b-instruct": ModelInfo(
        id="meta-llama/llama-3.1-70b-instruct",
        name="Llama 3.1 70B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.35,
        output_cost_per_million=0.40,
    ),
    "meta-llama/llama-3.1-8b-instruct": ModelInfo(
        id="meta-llama/llama-3.1-8b-instruct",
        name="Llama 3.1 8B",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.05,
        output_cost_per_million=0.08,
    ),
    "meta-llama/llama-3.1-8b-instruct:free": ModelInfo(
        id="meta-llama/llama-3.1-8b-instruct:free",
        name="Llama 3.1 8B (Free)",
        provider="meta",
        context_length=131072,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
    ),
    "meta-llama/llama-guard-3-8b": ModelInfo(
        id="meta-llama/llama-guard-3-8b",
        name="Llama Guard 3 8B",
        provider="meta",
        context_length=8192,
        input_cost_per_million=0.05,
        output_cost_per_million=0.05,
    ),
    # ==========================================================================
    # Mistral
    # ==========================================================================
    "mistralai/mistral-large-2411": ModelInfo(
        id="mistralai/mistral-large-2411",
        name="Mistral Large",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=2.00,
        output_cost_per_million=6.00,
    ),
    "mistralai/mistral-medium-3": ModelInfo(
        id="mistralai/mistral-medium-3",
        name="Mistral Medium 3",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=0.40,
        output_cost_per_million=2.00,
    ),
    "mistralai/mistral-small-2409": ModelInfo(
        id="mistralai/mistral-small-2409",
        name="Mistral Small",
        provider="mistral",
        context_length=32000,
        input_cost_per_million=0.20,
        output_cost_per_million=0.60,
    ),
    "mistralai/mistral-small-3.1-24b-instruct": ModelInfo(
        id="mistralai/mistral-small-3.1-24b-instruct",
        name="Mistral Small 3.1 24B",
        provider="mistral",
        context_length=96000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.30,
    ),
    "mistralai/ministral-8b": ModelInfo(
        id="mistralai/ministral-8b",
        name="Ministral 8B",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.10,
    ),
    "mistralai/ministral-3b": ModelInfo(
        id="mistralai/ministral-3b",
        name="Ministral 3B",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=0.04,
        output_cost_per_million=0.04,
    ),
    "mistralai/codestral-2501": ModelInfo(
        id="mistralai/codestral-2501",
        name="Codestral",
        provider="mistral",
        context_length=256000,
        input_cost_per_million=0.30,
        output_cost_per_million=0.90,
    ),
    "mistralai/codestral-mamba": ModelInfo(
        id="mistralai/codestral-mamba",
        name="Codestral Mamba",
        provider="mistral",
        context_length=256000,
        input_cost_per_million=0.25,
        output_cost_per_million=0.25,
    ),
    "mistralai/pixtral-large-2411": ModelInfo(
        id="mistralai/pixtral-large-2411",
        name="Pixtral Large",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=2.00,
        output_cost_per_million=6.00,
        supports_vision=True,
    ),
    "mistralai/pixtral-12b": ModelInfo(
        id="mistralai/pixtral-12b",
        name="Pixtral 12B",
        provider="mistral",
        context_length=128000,
        input_cost_per_million=0.10,
        output_cost_per_million=0.10,
        supports_vision=True,
    ),
    # ==========================================================================
    # Qwen
    # ==========================================================================
    "qwen/qwen-2.5-72b-instruct": ModelInfo(
        id="qwen/qwen-2.5-72b-instruct",
        name="Qwen 2.5 72B",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.35,
        output_cost_per_million=0.40,
    ),
    "qwen/qwen-2.5-32b-instruct": ModelInfo(
        id="qwen/qwen-2.5-32b-instruct",
        name="Qwen 2.5 32B",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.18,
        output_cost_per_million=0.18,
    ),
    "qwen/qwen-2.5-7b-instruct": ModelInfo(
        id="qwen/qwen-2.5-7b-instruct",
        name="Qwen 2.5 7B",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.05,
        output_cost_per_million=0.05,
    ),
    "qwen/qwen-2.5-coder-32b-instruct": ModelInfo(
        id="qwen/qwen-2.5-coder-32b-instruct",
        name="Qwen 2.5 Coder 32B",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.18,
        output_cost_per_million=0.18,
    ),
    "qwen/qwq-32b-preview": ModelInfo(
        id="qwen/qwq-32b-preview",
        name="QwQ 32B (Reasoning)",
        provider="qwen",
        context_length=32768,
        input_cost_per_million=0.12,
        output_cost_per_million=0.18,
    ),
    "qwen/qwen-2.5-72b-instruct:free": ModelInfo(
        id="qwen/qwen-2.5-72b-instruct:free",
        name="Qwen 2.5 72B (Free)",
        provider="qwen",
        context_length=131072,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
    ),
    "qwen/qwen-2-vl-72b-instruct": ModelInfo(
        id="qwen/qwen-2-vl-72b-instruct",
        name="Qwen 2 VL 72B",
        provider="qwen",
        context_length=32768,
        input_cost_per_million=0.40,
        output_cost_per_million=0.40,
        supports_vision=True,
    ),
    # ==========================================================================
    # Cohere
    # ==========================================================================
    "cohere/command-r-plus": ModelInfo(
        id="cohere/command-r-plus",
        name="Command R+",
        provider="cohere",
        context_length=128000,
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
    ),
    "cohere/command-r": ModelInfo(
        id="cohere/command-r",
        name="Command R",
        provider="cohere",
        context_length=128000,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
    ),
    "cohere/command-r7b-12-2024": ModelInfo(
        id="cohere/command-r7b-12-2024",
        name="Command R 7B",
        provider="cohere",
        context_length=128000,
        input_cost_per_million=0.0375,
        output_cost_per_million=0.15,
    ),
    # ==========================================================================
    # Perplexity
    # ==========================================================================
    "perplexity/sonar-pro": ModelInfo(
        id="perplexity/sonar-pro",
        name="Sonar Pro (Online)",
        provider="perplexity",
        context_length=200000,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
    ),
    "perplexity/sonar": ModelInfo(
        id="perplexity/sonar",
        name="Sonar (Online)",
        provider="perplexity",
        context_length=128000,
        input_cost_per_million=1.00,
        output_cost_per_million=1.00,
    ),
    "perplexity/sonar-reasoning": ModelInfo(
        id="perplexity/sonar-reasoning",
        name="Sonar Reasoning (Online)",
        provider="perplexity",
        context_length=128000,
        input_cost_per_million=1.00,
        output_cost_per_million=5.00,
    ),
    # ==========================================================================
    # AI21
    # ==========================================================================
    "ai21/jamba-1.5-large": ModelInfo(
        id="ai21/jamba-1.5-large",
        name="Jamba 1.5 Large",
        provider="ai21",
        context_length=256000,
        input_cost_per_million=2.00,
        output_cost_per_million=8.00,
    ),
    "ai21/jamba-1.5-mini": ModelInfo(
        id="ai21/jamba-1.5-mini",
        name="Jamba 1.5 Mini",
        provider="ai21",
        context_length=256000,
        input_cost_per_million=0.20,
        output_cost_per_million=0.40,
    ),
    # ==========================================================================
    # Amazon
    # ==========================================================================
    "amazon/nova-pro-v1": ModelInfo(
        id="amazon/nova-pro-v1",
        name="Amazon Nova Pro",
        provider="amazon",
        context_length=300000,
        input_cost_per_million=0.80,
        output_cost_per_million=3.20,
        supports_vision=True,
    ),
    "amazon/nova-lite-v1": ModelInfo(
        id="amazon/nova-lite-v1",
        name="Amazon Nova Lite",
        provider="amazon",
        context_length=300000,
        input_cost_per_million=0.06,
        output_cost_per_million=0.24,
        supports_vision=True,
    ),
    "amazon/nova-micro-v1": ModelInfo(
        id="amazon/nova-micro-v1",
        name="Amazon Nova Micro",
        provider="amazon",
        context_length=128000,
        input_cost_per_million=0.035,
        output_cost_per_million=0.14,
    ),
    # ==========================================================================
    # Microsoft
    # ==========================================================================
    "microsoft/phi-4": ModelInfo(
        id="microsoft/phi-4",
        name="Phi-4",
        provider="microsoft",
        context_length=16384,
        input_cost_per_million=0.07,
        output_cost_per_million=0.14,
    ),
    "microsoft/wizardlm-2-8x22b": ModelInfo(
        id="microsoft/wizardlm-2-8x22b",
        name="WizardLM 2 8x22B",
        provider="microsoft",
        context_length=65536,
        input_cost_per_million=0.50,
        output_cost_per_million=0.50,
    ),
    # ==========================================================================
    # Nous Research
    # ==========================================================================
    "nousresearch/hermes-3-llama-3.1-405b": ModelInfo(
        id="nousresearch/hermes-3-llama-3.1-405b",
        name="Hermes 3 405B",
        provider="nous",
        context_length=131072,
        input_cost_per_million=2.00,
        output_cost_per_million=2.00,
    ),
    "nousresearch/hermes-3-llama-3.1-70b": ModelInfo(
        id="nousresearch/hermes-3-llama-3.1-70b",
        name="Hermes 3 70B",
        provider="nous",
        context_length=131072,
        input_cost_per_million=0.35,
        output_cost_per_million=0.40,
    ),
    # ==========================================================================
    # Other Notable Models
    # ==========================================================================
    "nvidia/llama-3.1-nemotron-70b-instruct": ModelInfo(
        id="nvidia/llama-3.1-nemotron-70b-instruct",
        name="Nemotron 70B",
        provider="nvidia",
        context_length=131072,
        input_cost_per_million=0.35,
        output_cost_per_million=0.40,
    ),
    "databricks/dbrx-instruct": ModelInfo(
        id="databricks/dbrx-instruct",
        name="DBRX Instruct",
        provider="databricks",
        context_length=32768,
        input_cost_per_million=0.75,
        output_cost_per_million=0.75,
    ),
    "inflection/inflection-3-pi": ModelInfo(
        id="inflection/inflection-3-pi",
        name="Inflection 3 Pi",
        provider="inflection",
        context_length=8192,
        input_cost_per_million=0.80,
        output_cost_per_million=3.20,
    ),
    "sao10k/l3.3-euryale-70b": ModelInfo(
        id="sao10k/l3.3-euryale-70b",
        name="Euryale 70B",
        provider="sao10k",
        context_length=131072,
        input_cost_per_million=0.50,
        output_cost_per_million=0.60,
    ),
}


class OpenRouterProvider(BaseProvider):
    """OpenRouter - unified API for 400+ models.

    OpenRouter provides access to models from OpenAI, Anthropic, Google,
    Meta, Mistral, and many others through a single API endpoint.

    No markup on provider pricing - you pay what you'd pay directly.
    """

    provider_name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str | None = None):
        """Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key. If not provided, reads from
                     OPENROUTER_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ProviderError(
                "API key required. Set OPENROUTER_API_KEY or pass api_key.",
                provider=self.provider_name,
            )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://sandboxy.ai",
            "X-Title": "Sandboxy",
        }

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> ModelResponse:
        """Send completion request via OpenRouter."""
        start_time = time.time()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                error_body = e.response.text
                raise ProviderError(
                    f"HTTP {e.response.status_code}: {error_body}",
                    provider=self.provider_name,
                    model=model,
                ) from e
            except httpx.RequestError as e:
                raise ProviderError(
                    f"Request failed: {e}",
                    provider=self.provider_name,
                    model=model,
                ) from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response data
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        # Calculate cost if we have token counts
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = self._calculate_cost(model, input_tokens, output_tokens)

        return ModelResponse(
            content=message.get("content", ""),
            model_id=data.get("model", model),
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            finish_reason=choice.get("finish_reason"),
            raw_response=data,
        )

    async def stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream completion response."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        async with (
            httpx.AsyncClient(timeout=120.0) as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError):
                        continue

    def list_models(self) -> list[ModelInfo]:
        """List popular models available through OpenRouter."""
        return list(OPENROUTER_MODELS.values())

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float | None:
        """Calculate cost in USD for a request."""
        model_info = OPENROUTER_MODELS.get(model)
        if not model_info or not model_info.input_cost_per_million:
            return None

        input_cost = (input_tokens / 1_000_000) * model_info.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * model_info.output_cost_per_million
        return round(input_cost + output_cost, 6)

    async def fetch_models(self) -> list[dict[str, Any]]:
        """Fetch full model list from OpenRouter API.

        Returns live model data including pricing and availability.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

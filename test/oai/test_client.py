# Copyright (c) 2023 - 2024, Owners of https://github.com/ag2ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
#!/usr/bin/env python3 -m pytest

import os
import shutil
import time

import pytest

from autogen import OpenAIWrapper
from autogen.cache.cache import Cache
from autogen.oai.client import LEGACY_CACHE_DIR, LEGACY_DEFAULT_CACHE_SEED

from ..conftest import Credentials

TOOL_ENABLED = False
try:
    import openai
    from openai import OpenAI  # noqa: F401

    if openai.__version__ >= "1.1.0":
        TOOL_ENABLED = True
    from openai.types.chat.chat_completion import ChatCompletionMessage  # noqa: F401
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_aoai_chat_completion(credentials_azure_gpt_35_turbo: Credentials):
    config_list = credentials_azure_gpt_35_turbo.config_list
    client = OpenAIWrapper(config_list=config_list)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_completion_object(response))

    # test dialect
    config = config_list[0]
    config["azure_deployment"] = config["model"]
    config["azure_endpoint"] = config.pop("base_url")
    client = OpenAIWrapper(**config)
    response = client.create(messages=[{"role": "user", "content": "2+2="}], cache_seed=None)
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.openai
@pytest.mark.skipif(skip or not TOOL_ENABLED, reason="openai>=1.1.0 not installed")
def test_oai_tool_calling_extraction(credentials_gpt_4o_mini: Credentials):
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list)
    response = client.create(
        messages=[
            {
                "role": "user",
                "content": "What is the weather in San Francisco?",
            },
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "getCurrentWeather",
                    "description": "Get the weather in location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "The city and state e.g. San Francisco, CA"},
                            "unit": {"type": "string", "enum": ["c", "f"]},
                        },
                        "required": ["location"],
                    },
                },
            }
        ],
    )
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_chat_completion(credentials_gpt_4o_mini: Credentials):
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list)
    response = client.create(messages=[{"role": "user", "content": "1+1="}])
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_completion(credentials_azure_gpt_35_turbo_instruct: Credentials):
    client = OpenAIWrapper(config_list=credentials_azure_gpt_35_turbo_instruct.config_list)
    response = client.create(prompt="1+1=")
    print(response)
    print(client.extract_text_or_completion_object(response))


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
@pytest.mark.parametrize(
    "cache_seed",
    [
        None,
        42,
    ],
)
def test_cost(credentials_azure_gpt_35_turbo_instruct: Credentials, cache_seed):
    client = OpenAIWrapper(config_list=credentials_azure_gpt_35_turbo_instruct.config_list, cache_seed=cache_seed)
    response = client.create(prompt="1+3=")
    print(response.cost)


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_customized_cost(credentials_azure_gpt_35_turbo_instruct: Credentials):
    config_list = credentials_azure_gpt_35_turbo_instruct.config_list
    for config in config_list:
        config.update({"price": [1000, 1000]})
    client = OpenAIWrapper(config_list=config_list, cache_seed=None)
    response = client.create(prompt="1+3=")
    assert response.cost >= 4, (
        f"Due to customized pricing, cost should be > 4. Message: {response.choices[0].message.content}"
    )


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_usage_summary(credentials_azure_gpt_35_turbo_instruct: Credentials):
    client = OpenAIWrapper(config_list=credentials_azure_gpt_35_turbo_instruct.config_list)
    response = client.create(prompt="1+3=", cache_seed=None)

    # usage should be recorded
    assert client.actual_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"

    # check print
    client.print_usage_summary()

    # check clear
    client.clear_usage_summary()
    assert client.actual_usage_summary is None, "actual_usage_summary should be None"
    assert client.total_usage_summary is None, "total_usage_summary should be None"

    # actual usage and all usage should be different
    response = client.create(prompt="1+3=", cache_seed=42)
    assert client.total_usage_summary["total_cost"] > 0, "total_cost should be greater than 0"
    client.clear_usage_summary()
    response = client.create(prompt="1+3=", cache_seed=42)
    assert client.actual_usage_summary is None, "No actual cost should be recorded"

    # check update
    response = client.create(prompt="1+3=", cache_seed=42)
    assert client.total_usage_summary["total_cost"] == response.cost * 2, (
        "total_cost should be equal to response.cost * 2"
    )


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_legacy_cache(credentials_gpt_4o_mini: Credentials):
    # Prompt to use for testing.
    prompt = "Write a 100 word summary on the topic of the history of human civilization."

    # Clear cache.
    if os.path.exists(LEGACY_CACHE_DIR):
        shutil.rmtree(LEGACY_CACHE_DIR)

    # Test default cache seed.
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test with cache seed set through constructor
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list, cache_seed=13)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(13)))

    # Test with cache seed set through create method
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list)
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=17)
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time

    start_time = time.time()
    warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=17)
    end_time = time.time()
    duration_with_warm_cache = end_time - start_time
    assert cold_cache_response == warm_cache_response
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(17)))

    # Test using a different cache seed through create method.
    start_time = time.time()
    cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache_seed=21)
    end_time = time.time()
    duration_with_cold_cache = end_time - start_time
    assert duration_with_warm_cache < duration_with_cold_cache
    assert os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(21)))


@pytest.mark.openai
@pytest.mark.skipif(skip, reason="openai>=1 not installed")
def test_cache(credentials_gpt_4o_mini: Credentials):
    # Prompt to use for testing.
    prompt = "Write a 100 word summary on the topic of the history of artificial intelligence."

    # Clear cache.
    if os.path.exists(LEGACY_CACHE_DIR):
        shutil.rmtree(LEGACY_CACHE_DIR)
    cache_dir = ".cache_test"
    assert cache_dir != LEGACY_CACHE_DIR
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    # Test cache set through constructor.
    with Cache.disk(cache_seed=49, cache_path_root=cache_dir) as cache:
        client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list, cache=cache)
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}])
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_response == warm_cache_response
        assert duration_with_warm_cache < duration_with_cold_cache
        assert os.path.exists(os.path.join(cache_dir, str(49)))
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(49)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test cache set through method.
    client = OpenAIWrapper(config_list=credentials_gpt_4o_mini.config_list)
    with Cache.disk(cache_seed=312, cache_path_root=cache_dir) as cache:
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time

        start_time = time.time()
        warm_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_warm_cache = end_time - start_time
        assert cold_cache_response == warm_cache_response
        assert duration_with_warm_cache < duration_with_cold_cache
        assert os.path.exists(os.path.join(cache_dir, str(312)))
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(312)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))

    # Test different cache seed.
    with Cache.disk(cache_seed=123, cache_path_root=cache_dir) as cache:
        start_time = time.time()
        cold_cache_response = client.create(messages=[{"role": "user", "content": prompt}], cache=cache)
        end_time = time.time()
        duration_with_cold_cache = end_time - start_time
        assert duration_with_warm_cache < duration_with_cold_cache
        # Test legacy cache is not used.
        assert not os.path.exists(os.path.join(LEGACY_CACHE_DIR, str(123)))
        assert not os.path.exists(os.path.join(cache_dir, str(LEGACY_DEFAULT_CACHE_SEED)))


if __name__ == "__main__":
    # test_aoai_chat_completion()
    # test_oai_tool_calling_extraction()
    # test_chat_completion()
    test_completion()
    # # test_cost()
    # test_usage_summary()
    # test_legacy_cache()
    # test_cache()

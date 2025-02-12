# Copyright (c) 2023 - 2024, Owners of https://github.com/ag2ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
from .base import IOStream, InputStream, OutputStream
from .console import IOConsole
from .websockets import IOWebsockets

# Set the default input/output stream to the console
IOStream.set_global_default(IOConsole())
IOStream.set_default(IOConsole())

__all__ = ("IOConsole", "IOStream", "IOWebsockets", "InputStream", "OutputStream")

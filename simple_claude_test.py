#!/usr/bin/env python3
"""Simple Claude Code SDK Test Tool"""

import sys

# Test if claude-code-sdk is available
try:
    import anyio
    print("✓ anyio available")
except ImportError:
    print("✗ anyio not found - install with: pip install anyio")
    sys.exit(1)

try:
    from claude_code_sdk import query, ClaudeCodeOptions
    print("✓ claude-code-sdk available")
except ImportError:
    print("✗ claude-code-sdk not found - install with: pip install claude-code-sdk")
    sys.exit(1)

async def test_basic_query():
    """Test basic Claude query"""
    print("\n--- Testing Basic Query ---")
    
    try:
        options = ClaudeCodeOptions(max_turns=1)
        async for message in query(
            prompt="Say hello and tell me the current time", 
            options=options
        ):
            if hasattr(message, 'content') and hasattr(message.content, '__iter__'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(block.text, end='')
            elif hasattr(message, 'result'):
                print(message.result, end='')
        print("\n✓ Basic query successful")
    except Exception as e:
        print(f"✗ Basic query failed: {e}")

async def test_code_query():
    """Test code-related query"""
    print("\n--- Testing Code Query ---")
    
    try:
        options = ClaudeCodeOptions(max_turns=2)
        async for message in query(
            prompt="Write a simple Python function that adds two numbers", 
            options=options
        ):
            if hasattr(message, 'content') and hasattr(message.content, '__iter__'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(block.text, end='')
            elif hasattr(message, 'result'):
                print(message.result, end='')
        print("\n✓ Code query successful")
    except Exception as e:
        print(f"✗ Code query failed: {e}")

async def main():
    print("Claude Code SDK Test Tool")
    print("=" * 30)
    
    await test_basic_query()
    await test_code_query()
    
    print("\n" + "=" * 30)
    print("Test complete!")

if __name__ == "__main__":
    anyio.run(main)
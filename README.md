# PyMOL AI Copilot

Turn your PyMOL into an AI-powered assistant.

Supports:
- Chinese natural language
- English natural language
- Structure loading
- Alignment
- Surface analysis
- Ligand pocket highlighting
- Image rendering

## Installation

1. Install dependency

```bash
你的pymol目录/python.exe -m pip install openai
```

2. Configure API

Edit `ai_pymol.py`:

```python
api_key="YOUR_KEY"
```

3. Load plugin in PyMOL

```python
run 你的pymol目录/ai_pymol.py
```

## Example Usage

```python
ai 加载1ubq并显示为卡通
ai 加载1ubq和1ubi并对齐
ai 加载1m17并显示配体周围5埃范围的残基为棒状
```

## Architecture

```
Natural language
       ↓
LLM command generation
       ↓
Command validation
       ↓
Auto-fix
       ↓
Safe execution
```

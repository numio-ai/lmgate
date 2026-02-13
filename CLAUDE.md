# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

LMGate is a transparent pass-through proxy that sits between client applications and LLM API providers (OpenAI, Anthropic, Google, AWS). It controls access via API key allow-lists and collects usage statistics without modifying API calls. Python project (see .gitignore).

## Current State

Pre-implementation. The MVP specification is at `docs/lmgate specification.md`. No code, build system, or tests exist yet.

## Workflow

The steps to follow before implementation are:

1. You play the role of technical product manager and write functional and non-functional specification. This document later will serve as input for design by the engineering team. You can't get it right in one shot because of ambiguities. Therefore you write a draft and review it with the user. The user will provide their comments and updates, which you incorporate to update the document and review with the user again. This iterative process continues until the user accepts the spec and gives you the green light to proceed to step 2 "Design".
2. At the design step you write a design document as an implementation plan. It is important to distinguish design from coding. The design document doesn't contain code artifacts. It provides architecture views: how code is structured, how service components are structured, how we operate the system in production. You also collaborate with the user iteratively to get the design approved. After the design is approved you start implementation.

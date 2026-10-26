# ADR-001: Expo (React Native) with TypeScript strict and Expo Router for the mobile app

- Status: proposed
- Date: 2026-10-26
- Deciders: Orchestrator, mobile-engineer, project owner
- Related: E0-03, ADR-002, ADR-003, ADR-004, blueprint §4, §10

## Context

Capsule ships on iOS and Android to users aged 20–60. One developer plus agents builds it, so one codebase is a hard constraint. Targets from blueprint §10: cold start < 2 s on a mid-range Android, 60 fps, installed size < 60 MB, staged rollout and forced updates. The app needs camera, microphone, secure storage and streaming text, and must reach both stores without a Mac build farm.

## Options

1. **Expo (React Native) + TypeScript strict + Expo Router** — one TypeScript codebase; EAS Build makes iOS builds without a local Mac; EAS Update ships JS fixes over the air; file-based routing with typed routes; first-party camera, audio and secure-store modules. Cons: native modules outside the Expo SDK need a config plugin and a development build; bundle size has to be watched.
2. **Flutter** — excellent rendering performance and a mature widget set. Lost: Dart is a second language next to the Python backend and the TypeScript tooling, OpenAPI client generation is weaker, and its OTA option (Shorebird) is a third-party service, whereas EAS Update is part of the toolchain we already build with.
3. **Native Swift + Kotlin** — best platform fidelity. Lost: two codebases double the work for a one-person team, and every feature ships twice.

## Decision

Build the app with Expo (SDK pinned in `package.json` at project start; New Architecture only), TypeScript `strict` and Expo Router, run as a development build (expo-dev-client), not Expo Go; native code only through Expo config plugins or modules.

## Consequences

- Easier: one codebase, cloud builds, OTA fixes, types generated from `contracts/openapi.yaml`.
- Harder: upgrading the Expo SDK roughly twice a year; any library without New Architecture support needs a replacement; testers install development builds instead of Expo Go.
- We will monitor: cold start and slow frames per release (Sentry), installed size per EAS build, EAS Build and Update quota.
- Revisit when: p75 cold start stays > 2 s or slow frames > 1 % on the reference mid-range Android after two profiling iterations, or a must-have native capability has no Expo-compatible path.

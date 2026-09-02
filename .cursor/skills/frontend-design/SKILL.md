---
name: frontend-design
description: Guidance for distinctive, intentional visual design when building or reshaping UI. Use when creating React screens, restyling the app, or choosing palette, typography, and layout.
---

# Frontend Design

This app is a personal Instagram Stories scheduler: login, upload image/video + datetime, calendar of pending/published/failed. Audience is the account owner. The page's job is to schedule the next Story with confidence, not to look like a generic SaaS dashboard.

Approach this as the design lead at a small studio. Make deliberate, opinionated choices about palette, typography, and layout specific to this brief, and take one real aesthetic risk you can justify.

## Ground it in the subject

Name the subject (Stories que salen solas), the audience (quien opera la cuenta), and the screen's single job before designing. Pull visual language from Instagram Stories themselves: vertical 9:16 frames, a clock/calendar of when something goes live, status of a post — not from generic admin templates.

## Design principles

For web designs, the hero is a thesis. Open with the most characteristic thing: the next scheduled Story, a 9:16 preview, or the calendar of what is queued. A big number with a small label and a gradient accent is the template answer; only use it if it is truly the best option.

Typography carries personality. Pair display and body faces deliberately. Set a type scale with intentional weights and spacing.

Structure is information. Numbered markers (01 / 02 / 03) only if the content is actually a sequence. Status (pendiente / publicando / publicada / fallida) is the real structure here.

Leverage motion deliberately. Prefer one orchestrated moment over scattered effects. Respect `prefers-reduced-motion`.

Match complexity to the vision. Minimal directions need precision in spacing, type, and detail.

## Process: brainstorm, then build

AI-generated design clusters around three looks: (1) warm cream (#F4F1EA) + serif + terracotta; (2) near-black + acid-green or vermilion; (3) broadsheet hairline rules. Do not spend free axes on those defaults unless the brief asks for them.

Work in two passes. First, a compact token system:

- Color: 4–6 named hex values
- Type: display (restraint), body, utility for dates/status
- Layout: one-sentence concept + ASCII wireframe
- Signature: the one memorable element (e.g. a 9:16 preview strip in the calendar)

Review that plan against the brief. If it reads like the generic default for any similar page, revise it. Only then write code, deriving every color and type decision from the plan.

Watch CSS specificity: avoid classes that cancel each other (`.section` vs `button.cta` padding wars).

## Restraint and self-critique

Spend boldness in one place. Keep everything else quiet. Quality floor: responsive to mobile, visible keyboard focus, reduced motion respected.

## Copy

Write from the user's side of the screen. Name things by what people control: "Programar Story", "Cancelar", not "Create media container". Active voice. Same verb through the flow ("Publicar" → toast "Publicada"). Errors explain what went wrong and how to fix it; they do not apologize. Empty states invite the next action.

## Screens in this product

- Login (usuario / contraseña)
- Formulario: archivo + fecha/hora (`America/Bogota`)
- Calendario/listado con estado y cancelar si `pending`
- Aviso visible si el token de Instagram está por vencer

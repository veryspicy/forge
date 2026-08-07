# Stage 3 — Pet Profile ↔ AI Personalized Recommendations

**Date:** 2026-06-26
**Project:** Forge
**Base:** D:\codeRepo\forge

---

## Audit Findings (Task 1)

### 1.1 Pet Profile API — `pets.py`
All 5 endpoints (`GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`) correctly isolated via `user_id = Depends(get_current_user_id)`. The `PetService` layer uses `owner_id` for all queries.

### 1.2 AI Chat API — `ai_chat.py`
**Status: Mock only — required complete rewrite**

- `POST /chat` returned echo response with empty `recommendations: []`
- `POST /recommend` returned hardcoded sample data with random UUIDs
- Neither endpoint queried pet profiles or the product database

### 1.3 Pet Service — `pet_service.py`
Full CRUD + lifecycle auto-calculation. All methods filtered by `owner_id`. **No changes needed.**

### 1.4 AI Domain Services — `ai/services.py`
**Status: Empty — required complete rewrite**

Contained only two dataclasses (`AIRecommendation`, `ChatContext`) — zero business logic.

### 1.5 Frontend Pages

| File | Status |
|---|---|
| `pets.vue` | Pet list with inline wizard, no recommendation display |
| `chat.vue` | Mock implementation with `setTimeout` echo, no pet selector |
| `pets/wizard.vue` | Multi-step pet creation wizard — kept as-is |
| `pet.ts` store | Had `fetchPetRecommendations`, `setCurrentPet` — well-structured |
| `chat.ts` store | Had `sendMessage` with `pet_id` param — well-structured |
| `index.vue` | Only a text-link teaser for AI, no real recommendation section |

---

## Changes Made

### Task 2: Backend — Recommendation Engine

#### 2.1 `domain/ai/services.py` — Rewritten

Added `PetRecommendationEngine` class with:

| Method | Purpose |
|---|---|
| `extract_keywords(pet_profile)` | Maps breed→breed_group, lifecycle→search keywords, allergies→exclude terms |
| `generate_chat_response(...)` | Rule-based personalized chat reply referencing pet profile |
| `format_pet_context(...)` | Formats pet profile as human-readable context string |

Keyword dictionaries added:

- `LIFECYCLE_KEYWORDS`: PUPPY_KITTEN / ADULT / SENIOR → product search terms
- `ALLERGY_TAG_MAP`: allergy name → tags to exclude from results
- `HEALTH_KEYWORDS`: health note keywords → search terms
- `CATEGORY_FOR_BREED_GROUP`: breed group → default category

Scoring strategy (3-tier):

| Priority | Method | Confidence |
|---|---|---|
| 1 | `list_by_breed_group()` | 0.9 |
| 2 | `search(breed_name)` | 0.7 |
| 3 | `search(lifecycle_kw)` | 0.6 |

#### 2.2 `api/v1/ai_chat.py` — Rewritten

**`POST /chat`** — Now:
- Accepts `message`, optional `conversation_id`, optional `pet_id`
- If `pet_id` provided → fetches that pet profile (owner-verified)
- If no `pet_id` → auto-selects user's first pet
- Extracts keywords, queries product DB via `ProductRepository.search()` and `list_by_breed_group()`
- Filters out products with allergen tags
- Scores/deduplicates/sorts by confidence, returns top 5
- Generates personalized chat response
- Response includes `response`, `conversation_id`, `recommendations[]`

**`POST /recommend`** — Now:
- Accepts `pet_id` and `limit` (default 5, max 20)
- Fetches pet profile (owner-verified), runs same recommendation pipeline
- Returns `RecommendationItem[]` with `product_id`, `product_name`, `reason`, `confidence`

#### 2.3 `api/v1/pets.py` — Extended

Added new endpoint: **`GET /{pet_id}/recommendations`**
- Query param: `limit` (default 5, range 1-20)
- Runs the same keyword-based recommendation pipeline
- Returns `RecommendationItem[]`
- This endpoint is what the frontend `useApi.fetchPetRecommendations()` calls

---

### Task 3: Frontend — Pet Page + Chat Page

#### 3.1 `pages/pets.vue` — Modified

Each pet card now has a **"Tailored for {name}"** recommendation section:

- **If no recommendations loaded**: Shows a "View recommendations" button
- **On click**: Calls `GET /pets/{id}/recommendations` (via `useApi.fetchPetRecommendations`)
- **Loading state**: Animated skeleton placeholder
- **Recommendations loaded**: Up to 3 product cards showing:
  - Product name (truncated)
  - Reason (truncated)
  - Confidence percentage badge
- **Click**: Navigates to `/products/{product_id}`
- State tracked per-pet via `recLoading` and `petRecs` refs

#### 3.2 `pages/chat.vue` — Modified

**Pet selector** added at top:
- Horizontal button bar listing all user's pets
- First pet auto-selected on mount
- Active pet highlighted with primary color
- Tooltip: "AI will use this pet's profile for personalized recommendations"
- Empty state fallback if no pets exist

**Recommendation cards** rendered inline:
- When AI response includes `recommendations[]`, renders clickable product cards
- Shows product name, reason, confidence badge
- Click navigates to `/products/{product_id}`

**API integration**:
- Calls `useApi.aiChat({ message, pet_id })` with proper object parameter
- Handles loading state (bouncing dots animation)
- Error handling with fallback message
- Real scroll-to-bottom after each message

---

### Task 4: Homepage — `pages/index.vue` — Modified

Added **"Tailored for Your Pet"** section between hero and categories:

- **Visibility**: Only shown when user is logged in (`localStorage` token exists) AND has at least one pet profile
- **Content**: First pet's top 4 recommendations displayed as product cards
- **Card style**: Matches product list — icon placeholder, product name, reason, confidence badge
- **Empty state**: Falls back to "No recommendations yet" with link to pets page
- **Loading**: Shows animated placeholder while fetching
- **"Ask AI for more →"** link to chat page
- Calls `fetchPetRecommendations(firstPetId)` on mount

---

### Task 5: Documentation — `STAGE3-DONE.md`

This file (created at project root).

---

## Full Change Summary

| Step | File | Change |
|---|---|---|
| 1.1-1.5 | — | Audit only (no changes to existing files) |
| 2.1 | `backend/src/forge/domain/ai/services.py` | **Rewritten** — Added `PetRecommendationEngine` + keyword mapping dicts |
| 2.2 | `backend/src/forge/api/v1/ai_chat.py` | **Rewritten** — Real pet-aware recommendation pipeline for `/chat` and `/recommend` |
| 2.3 | `backend/src/forge/api/v1/pets.py` | **Extended** — Added `GET /{pet_id}/recommendations` endpoint |
| 3.1 | `portal-web/app/pages/pets.vue` | **Modified** — Added per-pet recommendation section below each card |
| 3.2 | `portal-web/app/pages/chat.vue` | **Modified** — Added pet selector + recommendation card rendering |
| 4 | `portal-web/app/pages/index.vue` | **Modified** — Added "Tailored for Your Pet" section |
| 5 | `STAGE3-DONE.md` | **Created** — This document |

### Files NOT modified

| File | Reason |
|---|---|
| `pets/wizard.vue` | Already functional, no recommendation integration needed at creation time |
| `pets/new.vue` | Simple form, not in recommendation flow |
| `stores/pet.ts` | Already had `setCurrentPet`, `fetchPetRecommendations`, `loadRecommendations` |
| `stores/chat.ts` | Already had `sendMessage` with `pet_id` parameter |
| `application/services/pet_service.py` | Already correctly isolated by `owner_id` |

---

## Architecture Note

The recommendation engine uses a **rule-based keyword matching** approach (not an actual LLM call) because:

1. The project has no OpenAI/LLM API key configured
2. The product database query methods (`search`, `list_by_breed_group`) are fast and deterministic
3. Keyword extraction from pet profiles (breed→group, lifecycle→tags, allergies→exclusions) produces reasonable product matches without an LLM
4. The `PetRecommendationEngine` is designed as a standalone class that could later serve as a pre-filter before calling a real LLM for ranking

If an LLM integration is added later, the engine can be used to gather candidate products (top 20), then the LLM can re-rank and explain each recommendation.

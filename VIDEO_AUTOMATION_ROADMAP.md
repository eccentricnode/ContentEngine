# Content Engine - Video Automation Roadmap

## Vision

Transform written content (blog posts, articles, zettelkasten notes) into high-quality video content automatically through an integrated pipeline combining AI image generation, video scene creation, talking head videos, automated music generation, and intelligent composition.

---

## Current State

**What Exists:**
- ContentEngine infrastructure (CLI, database, agents)
- Blog post content ready for transformation
- Prompt engineering templates (two-paths diagram, zettelkasten revelation)

**What Works:**
- Manual workflow: Blog post → Image prompts → Generated images (via nano banana pro/Midjourney)
- Manual video creation: Images → Veo 3 scenes (8 sec clips)
- Manual composition: ffmpeg stitching

---

## Future Automated Pipeline

### Phase 1: Content-to-Prompts Engine (Foundation)

**Goal:** Automatically transform written content into image generation prompts

**Components:**
1. **Content Analyzer**
   - Parse markdown blog posts
   - Extract key concepts, sections, and insights
   - Identify visualization opportunities
   - Map narrative structure

2. **Prompt Generator**
   - Template library for different diagram types:
     - Workflow diagrams
     - Comparison visuals (before/after, wrong/right)
     - Concept explanations
     - Data visualizations
   - LLM-powered prompt crafting
   - Style consistency across prompts

3. **Output:**
   - Structured prompt sets for each blog post
   - Metadata linking prompts to content sections
   - Priority ranking (which visuals are most critical)

**Tech Stack:**
- Python 3.11+
- Claude API for prompt generation
- Template engine (Jinja2)
- Content parser (markdown-it-py)

**Estimated Timeline:** 2-4 weeks

---

### Phase 2: Image Generation Integration

**Goal:** Automatically generate images from prompts via API

**Components:**
1. **Image Generation Orchestrator**
   - API integrations:
     - Midjourney (via third-party APIs)
     - DALL-E 3 (OpenAI)
     - Stable Diffusion (local or API)
   - Queue management for batch processing
   - Result validation and quality checks

2. **Asset Manager**
   - Store generated images with metadata
   - Version control for iterations
   - Tagging and categorization
   - Content-to-image linkage

**Tech Stack:**
- Midjourney API (replicate.com or mj.run)
- OpenAI DALL-E 3 API
- PostgreSQL for asset metadata
- S3/local storage for image files

**Estimated Timeline:** 2-3 weeks

---

### Phase 3: Video Scene Generation

**Goal:** Transform static images into animated video scenes

**Components:**
1. **Video Generation Router**
   - Provider selection logic:
     - Veo 3 (via Vertex AI) - highest quality
     - Runway Gen-4 - 4K output
     - Pika 2.5 - speed/cost optimization
   - Fallback handling
   - Cost optimization (use cheaper providers when appropriate)

2. **Scene Orchestrator**
   - Batch video generation from image sets
   - Polling and status tracking
   - Duration management (4-10 sec per scene)
   - Scene transition planning

3. **Scene Library**
   - Database of generated scenes
   - Reusability for similar content
   - Quality ratings and analytics

**Tech Stack:**
- Google Vertex AI (Veo 3)
- Runway API
- Pika API
- Async task queue (Celery + Redis)
- PostgreSQL scene metadata

**Estimated Timeline:** 3-4 weeks

---

### Phase 4: Talking Head Generation

**Goal:** Create presenter videos from scripts

**Options:**

**Option A: AI Avatar (Fully Automated)**
- Use SadTalker (open-source) or D-ID API
- Generate talking head from single photo + audio
- Pros: Fully automated, scalable
- Cons: Uncanny valley risk, less authentic

**Option B: Human Recording (Hybrid)**
- Record yourself presenting the script
- Template setup for consistent framing/lighting
- Teleprompter integration for script reading
- Pros: Authentic, engaging
- Cons: Requires manual recording step

**Components:**
1. **Script Generator**
   - Transform blog content into spoken script
   - Pacing optimization for video
   - Natural language flow

2. **Avatar/Recording Pipeline**
   - AI avatar generation (SadTalker/D-ID)
   - OR Recording template system
   - Audio generation (ElevenLabs or gTTS)
   - Lip-sync processing

3. **Presenter Asset Library**
   - Store recorded segments
   - Build reusable intro/outro clips
   - Transition templates

**Tech Stack:**
- SadTalker (local GPU)
- D-ID API (commercial)
- ElevenLabs API (voiceover)
- gTTS (free TTS fallback)
- OBS Studio automation (for recording)

**Estimated Timeline:** 3-5 weeks

---

### Phase 5: Music Generation & Audio

**Goal:** Automated background music creation and audio mixing

**Components:**
1. **Music Generator**
   - Suno API integration (via SunoAPI.org)
   - Prompt templates for different video moods:
     - Calm/ambient (explanatory content)
     - Energetic (motivational content)
     - Dramatic (storytelling)
   - Duration matching to video length
   - Instrumental-only mode

2. **Audio Mixer**
   - Voiceover + background music mixing
   - Dynamic ducking (lower music during speech)
   - Volume normalization
   - Audio mastering

3. **Sound Library**
   - Generated music archive
   - Reusable tracks for similar content
   - License management

**Tech Stack:**
- Suno API (SunoAPI.org or MusicAPI.ai)
- Meta MusicGen (local fallback)
- FFmpeg for audio processing
- librosa (audio analysis)
- pydub (audio manipulation)

**Estimated Timeline:** 2-3 weeks

---

### Phase 6: Video Composition Engine

**Goal:** Intelligently compose all elements into final video

**Components:**
1. **Composition Planner**
   - Analyze content structure
   - Determine optimal layout:
     - Talking head + B-roll scenes
     - Scene transitions
     - Text overlay timing
   - Timeline generation

2. **FFmpeg Automation**
   - Scene concatenation
   - Talking head overlay positioning
   - Music mixing with ducking
   - Text/caption rendering
   - Transition effects
   - Color grading

3. **Rendering Pipeline**
   - Multi-quality output (1080p, 4K)
   - Platform optimization (YouTube, Instagram, TikTok)
   - Thumbnail generation
   - Preview clips

**Tech Stack:**
- FFmpeg (core compositor)
- MoviePy (Python orchestration)
- Pillow (text rendering)
- Async rendering queue
- GPU acceleration (NVENC)

**Estimated Timeline:** 4-6 weeks

---

### Phase 7: End-to-End Automation

**Goal:** Single command to transform blog post → published video

**Components:**
1. **Master Pipeline Orchestrator**
   ```bash
   content-engine video generate \
     --input "Blog-Post-Zettelkasten-Revelation-Final.md" \
     --style "educational" \
     --duration "10-15min" \
     --output "output/zettelkasten-video.mp4"
   ```

2. **Workflow Engine**
   - Phase 1: Content → Prompts (30 sec)
   - Phase 2: Prompts → Images (5-10 min)
   - Phase 3: Images → Video Scenes (10-20 min)
   - Phase 4: Generate talking head (5 min OR manual recording)
   - Phase 5: Generate background music (2-3 min)
   - Phase 6: Compose final video (5-10 min)
   - **Total:** ~30-50 minutes automated

3. **Quality Control**
   - Preview generation at each stage
   - Manual approval gates (optional)
   - Iteration support
   - A/B variant generation

4. **Publishing Integration**
   - YouTube API upload
   - Automatic metadata (title, description, tags)
   - Thumbnail upload
   - Playlist management

**Tech Stack:**
- Celery + Redis (task queue)
- PostgreSQL (state tracking)
- Web UI (monitoring dashboard)
- YouTube Data API v3
- Webhook notifications

**Estimated Timeline:** 3-4 weeks

---

## Cost Analysis

### Per-Video Cost Breakdown (15-min video)

| Component | Cost | Notes |
|-----------|------|-------|
| **Image Generation** | $2-5 | 15-20 images via Midjourney/DALL-E |
| **Video Scenes** | $15-20 | 20 scenes @ Runway ($0.96 ea) |
| **Talking Head** | $0-2 | SadTalker free / D-ID $1-2 |
| **Voiceover** | $0-3 | gTTS free / ElevenLabs $2-3 |
| **Music** | $0.01-0.04 | Suno API or MusicGen free |
| **Processing** | $0 | Local compute/ffmpeg |
| **Total** | **$17-30** | Full automation |

### Cost Optimization Strategies

1. **Use cheaper providers when quality allows:**
   - Pika 2.5 ($8/mo unlimited) instead of per-scene pricing
   - MusicGen (local, free) instead of Suno API
   - gTTS (free) instead of ElevenLabs

2. **Asset reuse:**
   - Cache similar scenes/music
   - Reuse intro/outro segments
   - Template libraries

3. **Batch processing:**
   - Generate multiple videos together
   - Optimize API quota usage

**Optimized cost:** **$5-15 per video**

---

## Technical Requirements

### Infrastructure

**Required:**
- Ubuntu/Debian Linux server or local machine
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- FFmpeg with GPU support (NVENC/VAAPI)
- 500GB+ storage for assets

**Optional:**
- GPU for local ML (MusicGen, SadTalker)
  - NVIDIA RTX 3060+ (12GB VRAM)
  - OR AMD equivalent
- S3/CloudFlare R2 for cloud storage
- Monitoring (Prometheus + Grafana)

### API Keys Needed

- Claude API (prompt generation)
- Midjourney API or DALL-E 3
- Veo 3 (Vertex AI) or Runway API
- Suno API (SunoAPI.org)
- ElevenLabs (optional)
- D-ID API (optional)
- YouTube Data API v3

---

## Development Roadmap

### Timeline Overview

| Phase | Duration | Dependencies | Cost |
|-------|----------|--------------|------|
| Phase 1: Content → Prompts | 2-4 weeks | Claude API | $10-50/mo |
| Phase 2: Image Generation | 2-3 weeks | Phase 1 | $20-100/mo |
| Phase 3: Video Scenes | 3-4 weeks | Phase 2 | $100-300/mo |
| Phase 4: Talking Head | 3-5 weeks | None (parallel) | $0-30/mo |
| Phase 5: Music & Audio | 2-3 weeks | None (parallel) | $8-30/mo |
| Phase 6: Composition | 4-6 weeks | Phase 3-5 | $0 |
| Phase 7: End-to-End | 3-4 weeks | All phases | $0 |
| **Total** | **16-24 weeks** | | **$138-510/mo** |

### Parallel Development Strategy

**Track 1 (Critical Path):**
- Phase 1 → Phase 2 → Phase 3 → Phase 6 → Phase 7

**Track 2 (Parallel):**
- Phase 4 (Talking Head)
- Phase 5 (Music/Audio)

**Estimated real-world timeline:** 4-6 months with parallel development

---

## Success Metrics

### Quality Metrics
- Video completion rate (% of generated videos meeting quality bar)
- Manual intervention rate (% requiring human fixes)
- Viewer retention (YouTube analytics)
- Engagement rate (likes, comments, shares)

### Performance Metrics
- End-to-end generation time (target: <1 hour)
- Cost per video (target: <$15)
- Success rate (% of generations completing without errors)
- Asset reuse rate (% of scenes/music reused)

### Business Metrics
- Videos generated per week
- Total content output (minutes of video)
- Cost savings vs manual production
- Revenue per video (if monetized)

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API rate limits | High | Medium | Implement queuing, multiple providers |
| Video quality inconsistency | Medium | High | Manual review gates, quality scoring |
| Audio sync issues | Medium | High | Validation layer, fallback to manual |
| Cost overruns | Medium | Medium | Budget monitoring, cost caps |
| Provider API changes | Low | High | Multi-provider abstraction layer |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Content-prompt mismatch | Medium | Medium | Human review, iteration loops |
| Scalability bottlenecks | Low | Medium | Queue-based architecture |
| Storage overflow | Medium | Low | Auto-cleanup, cloud storage |
| GPU availability | Low | Medium | Fallback to cloud APIs |

---

## Next Steps

### Immediate (Week 1-2)
1. ✅ Research complete (Veo 3, Suno, alternatives)
2. ✅ Proof of concept (manual workflow validated)
3. ⬜ Set up development environment
4. ⬜ Initialize Phase 1 (Content-to-Prompts)

### Short Term (Month 1-2)
1. ⬜ Complete Phase 1 + Phase 2 (Image generation)
2. ⬜ Build basic video composition (Phase 6 MVP)
3. ⬜ Test end-to-end with 1-2 blog posts manually

### Medium Term (Month 3-4)
1. ⬜ Complete Phase 3 (Video scenes)
2. ⬜ Complete Phase 5 (Music/audio)
3. ⬜ Integrate all components
4. ⬜ Generate first fully automated video

### Long Term (Month 5-6)
1. ⬜ Complete Phase 4 (Talking head)
2. ⬜ Complete Phase 7 (End-to-end automation)
3. ⬜ Production testing (10+ videos)
4. ⬜ Launch content calendar automation

---

## Open Questions

1. **Talking head approach:** AI avatar vs manual recording?
   - Decision point: After Phase 3 completion
   - Test both approaches with sample content

2. **Video length strategy:** Focus on short-form (<5min) or long-form (10-15min)?
   - Decision point: After cost analysis of Phase 3
   - May need different workflows for different lengths

3. **Publishing automation:** Auto-publish or manual approval?
   - Decision point: Phase 7
   - Start with manual approval, automate after confidence builds

4. **Monetization:** YouTube ads, sponsorships, or lead generation?
   - Decision point: After 20+ videos generated
   - Measure engagement before deciding strategy

---

## Related Documents

- `/home/ajohnson/Documents/Folio/1-Projects/two-paths-diagram-prompts.md` - Example prompt set
- `/home/ajohnson/Documents/Folio/1-Projects/zettelkasten-revelation-diagram-prompts.md` - Example prompt set
- `/home/ajohnson/Documents/Folio/1-Projects/zettelkasten-revelation-video-script.md` - Example video script
- `/home/ajohnson/Documents/Folio/1-Projects/Blog-Post-Zettelkasten-Revelation-Final.md` - Source content

---

## Notes

**Last Updated:** 2026-01-14

**Status:** Planning / Research Complete

**Next Milestone:** Phase 1 Development Start

**Owner:** AJ

**Priority:** High - Strategic content multiplier

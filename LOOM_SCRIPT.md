# Loom Video Script - Content Engine Introduction

**Target:** Vixxo PE role (and other AI engineering interviews)
**Duration:** 5-7 minutes
**Tone:** Confident, technical, teaching-focused

---

## Part 1: Hook (30 seconds)

**[Screen: Face cam OR GitHub repo]**

> "Hi, I'm Austin Johnson. I built Content Engine - an AI-powered content posting system - in 8 hours using AI-first development with Claude Code.
>
> This isn't just a code demo. This is how I work, how I think about AI as a force multiplier, and how I'd teach your teams to work 2-3x faster.
>
> Let me show you."

**[Transition to screen share: GitHub repo]**

---

## Part 2: What It Does (1 minute)

**[Screen: GitHub README or terminal]**

> "Content Engine is an autonomous content posting system with human-in-the-loop approval.
>
> Here's the flow:
> - AI generates draft posts from my daily work
> - I review and approve (or reject)
> - System posts immediately or on schedule
> - Background worker handles automation
>
> It's LinkedIn today, Twitter and blog coming next.
>
> But the interesting part isn't what it does - it's how it was built."

**[Transition to: Terminal demo]**

---

## Part 3: Live Demo (2 minutes)

**[Screen: Terminal with CLI]**

> "Let me show you the CLI I built in 4 hours with AI.
>
> **[Type: content-engine draft "Just shipped Content Engine Phase 1.5"]**
>
> Draft created. Let's see all posts:
>
> **[Type: content-engine list]**
>
> Here's my draft. Full details:
>
> **[Type: content-engine show 1]**
>
> Now I'll approve it. Dry run first:
>
> **[Type: content-engine approve 1 --dry-run]**
>
> Looks good. Actually post:
>
> **[Type: content-engine approve 1]**
>
> **[Show: Success message, LinkedIn post ID]**
>
> Posted to LinkedIn. That's the system working."

**[Transition to: GitHub code]**

---

## Part 4: Architecture Decisions (2 minutes)

**[Screen: GitHub repo, show file structure]**

> "Now let me explain what I decided versus what AI handled.
>
> **What I decided:**
>
> **[Point to: pyproject.toml]**
> - Python over TypeScript (better AI/ML ecosystem)
>
> **[Point to: lib/database.py]**
> - SQLite for MVP, SQLAlchemy ORM for PostgreSQL scaling later
>
> **[Point to: cli.py]**
> - CLI-first, web UI later (ship what's valuable first)
>
> **[Point to: lib/database.py - OAuthToken model]**
> - Database-backed OAuth (not just .env files)
>
> **What AI handled:**
>
> **[Point to: agents/linkedin/oauth_server.py]**
> - Complete OAuth 2.0 implementation
>
> **[Point to: cli.py]**
> - All CLI commands, argument parsing
>
> **[Point to: lib/database.py]**
> - SQLAlchemy models, queries
>
> **[Point to: tests/]**
> - Test suite (4 tests passing)
>
> **[Point to: scripts/deploy.sh]**
> - Deployment script
>
> I designed the architecture. AI implemented it. I validated everything.
>
> That's AI-first development: I'm the architect, AI is the executor, I'm the validator."

**[Transition to: git log or ARCHITECTURE.md]**

---

## Part 5: AI-First Process (1.5 minutes)

**[Screen: ARCHITECTURE.md or git commit history]**

> "Look at the commit messages. Every commit says:
>
> **[Show: 'Co-Authored-By: Claude Sonnet 4.5']**
>
> This is how AI-first development works:
>
> **Step 1: I direct the architecture**
> - 'Build a CLI with Click that has draft, approve, schedule commands'
> - 'Create SQLAlchemy models for posts and OAuth tokens'
>
> **Step 2: AI implements**
> - Writes the code in minutes
> - Handles boilerplate, error handling, logging
>
> **Step 3: I validate**
> - Review for correctness
> - Test edge cases
> - Ensure it matches my intent
>
> **Step 4: We iterate**
> - 'Add dry-run mode to approve command'
> - 'Fix Pydantic deprecation warnings'
>
> **Result:** 8 hours instead of 2-3 days. 2-3x faster.
>
> **[Show: ARCHITECTURE.md time breakdown]**
>
> Phase 1: 2 hours
> Phase 1.5: 4 hours
> Testing: 1 hour
> Documentation: 1 hour
>
> Total: 8 hours for a production-ready system."

**[Transition to: Face cam or GitHub repo]**

---

## Part 6: How This Applies to [Company Name] (1 minute)

**[Screen: Face cam OR slide with company name]**

> "This is the same approach I'd use at [Vixxo / Your Company].
>
> **Example scenario:**
> Your ops team spends 10 hours/week manually compiling equipment status reports.
>
> **My approach:**
> 1. Interview ops team - understand the workflow, pain points
> 2. Design the system - database schema, API endpoints, notification triggers
> 3. Use AI to build it - implement in days instead of weeks
> 4. Validate with ops team - does it solve the problem?
> 5. Iterate - refine based on real usage
>
> **Traditional development:** 2-3 weeks, expensive
> **AI-first development:** 3-5 days, validated with real users
>
> That's the shift I'd help your teams make."

**[Transition to: Face cam for closing]**

---

## Part 7: Closing (30 seconds)

**[Screen: Face cam]**

> "Content Engine demonstrates:
> - AI-first development (2-3x faster)
> - Production architecture (error handling, logging, testing, deployment)
> - System design thinking (database, CLI, workers, separation of concerns)
> - And most importantly: teaching ability
>
> I can show your teams how to work this way.
>
> GitHub repo: [link in description]
> LinkedIn: [your profile]
>
> Let's talk about how we'd apply this at [Company Name].
>
> Thanks for watching."

---

## Technical Setup Notes

**Recording Setup:**
- Screen resolution: 1920x1080 (or 1440p)
- Terminal: Increase font size (14-16pt minimum)
- Browser: Zoom to 125-150%
- Audio: Test mic levels (clear, no background noise)
- Lighting: Face well-lit if using cam

**Screen Sharing Tips:**
- Hide sensitive info (.env files, personal data)
- Close unnecessary tabs/windows
- Use full screen terminal for demos
- Slow down typing (watchers need to read)
- Pause after key points (let info sink in)

**Editing (Optional):**
- Cut long pauses
- Speed up slow parts (terminal output)
- Add text callouts for key points
- Add chapters/timestamps in description

---

## Checklist Before Recording

- [ ] Run through script once (practice)
- [ ] Test CLI commands work
- [ ] LinkedIn OAuth is working
- [ ] Terminal font is large enough
- [ ] Audio levels tested
- [ ] No sensitive data visible
- [ ] GitHub repo is public
- [ ] All files committed
- [ ] ARCHITECTURE.md is complete
- [ ] Confident about talking points

---

## Customization by Company

**For Vixxo PE role:**
- Emphasize: Teaching/coaching ability
- Example: "Help ops teams automate manual processes"
- Tone: Transformation-focused

**For Contract AI Engineer roles:**
- Emphasize: Fast delivery, production quality
- Example: "Ship features in days instead of weeks"
- Tone: Results-focused

**For Nuclear Startup:**
- Emphasize: System architecture, safety-critical thinking
- Example: "Build reliable automation for critical systems"
- Tone: Engineering rigor

---

## After Recording

**Distribution:**
1. Upload to Loom
2. Set privacy: "Anyone with link"
3. Copy link
4. Add to:
   - Email to Vixxo recruiter
   - LinkedIn message to Derek Neighbors
   - Cover letter for other applications
   - GitHub repo README (optional)

**Follow-up:**
- Send with message: "Made you a quick intro video showing how I work"
- Don't over-explain, let video speak
- Be ready to discuss in interview

---

**Goal:** Demonstrate you're not just an engineer who uses AI - you're someone who can transform how teams work.

**Key Message:** "I can teach your teams to work this way. 2-3x faster. Higher quality. Let's talk."

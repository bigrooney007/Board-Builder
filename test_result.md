#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
user_problem_statement: >
  Phase 2 of Nonprofit Board Builder: homepage corrections (hero buttons removed, prominent
  three-stage CTAs, screenshot section removed, Rooney Calendly CTA), testimonial carousels on all
  3 landing + 3 options pages, step-by-step multi-step public forms for all three funnels,
  simplified Recruitment funnel (new 3-step form, no insight page, direct redirect to
  /recruit/options), Recruitment paid-member platform: member auth (register/login/logout/
  forgot/reset), Stripe TEST MODE server-side verification and entitlements (recruitment_basic $97,
  recruitment_self_guided $497, live flags false), customer dashboard, $97 course (6 modules,
  resources, LinkedIn launch instructions, video placeholders, progress tracking), $497 course
  shell (6 modules, disabled Phase-3 tool placeholders), support request box under every module
  emailing the owner, server-side access control. Board Applicant Network untouched.

backend:
  - task: "Recruitment funnel lead API with new 3-step question schema"
    implemented: true
    working: "NA"
    file: "/app/backend/funnel_service.py, /app/backend/funnel_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "REQUIRED_ANSWERS recruitment changed to new_members_needed, present_board, active_board, board_type, accomplish, strengthen_areas, timeline. Lead saves with offer_source=recruitment, owner email sent. Manually smoke-tested once (201 + email Sent)."
  - task: "Payment config + checkout gating with RECRUITMENT_97_LIVE/RECRUITMENT_497_LIVE flags and /purchase/success redirect"
    implemented: true
    working: "NA"
    file: "/app/backend/payment_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/payments/config returns recruitment_97_live/recruitment_497_live (both false). Recruitment checkout requires flag true OR internal_test with admin auth. Recruitment success_url now /purchase/success?session_id=..."
  - task: "Member authentication (register/login/logout/me/forgot-password/reset-password)"
    implemented: true
    working: "NA"
    file: "/app/backend/member_routes.py, /app/backend/member_auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "JWT member sessions via member_access_token cookie + Bearer fallback. bcrypt hashing. Password reset tokens in password_resets collection, emailed via Resend."
  - task: "Purchase claim with server-side Stripe verification and entitlements"
    implemented: true
    working: "NA"
    file: "/app/backend/member_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "claim_recruitment_purchase retrieves Stripe session server-side, requires payment_status=paid, maps tier 97->recruitment_basic / 497->recruitment_self_guided, saves purchases record (user, lead, customer, session, payment intent, tier, product, amount, status, date), associates lead with member. Unpaid session must return 402."
  - task: "Course APIs with entitlement enforcement, video config, progress tracking"
    implemented: true
    working: "NA"
    file: "/app/backend/course_routes.py, /app/backend/course_content.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/courses/recruitment/basic (recruitment_basic OR self_guided), GET /api/courses/recruitment/self-guided (self_guided only), unauthenticated -> 401, wrong entitlement -> 403. POST /api/courses/progress (viewed/completed). youtube_url merged from course_videos collection (PATCH /api/admin/course-videos, admin only). Basic has 6 modules with resources incl LinkedIn 10-step instructions and Module 6 agreements; self-guided has 6 shells with disabled_tools."
  - task: "Support requests saved and emailed to owner"
    implemented: true
    working: "NA"
    file: "/app/backend/course_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/support-requests (member auth + entitlement). Saves ID, user, name, org, email, tier, product, module, type, message, date, status New. Emails owner with subject 'New Board Builder Support Request — [Org] — Module [X]'."
  - task: "Board Applicant Network unchanged"
    implemented: true
    working: "NA"
    file: "/app/backend/applicant_routes.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "No changes made; verify join-a-board applicant POST still works."

frontend:
  - task: "Homepage corrections (hero buttons removed, prominent stage CTAs, screenshot section removed, Rooney Calendly button)"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/LandingPage.jsx, FounderStorySection.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Hero OfferChoices removed, stage buttons now .button.stage-cta, ProductToolsSection removed from homepage (file kept), founder section has single Book a Call With Rooney -> https://calendly.com/boardbuilder/recruitboard target _blank."
  - task: "Testimonial carousels on 3 landing pages + 3 options pages"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/components/TestimonialCarousel.jsx, testimonialsData.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Shared exact testimonials, prev/next arrows, dots, autoplay, touch swipe. Landing heading: 'Nonprofit Leaders We Have Helped Build Stronger Boards'; options heading: 'See What Other Nonprofit Leaders Have Accomplished'."
  - task: "Multi-step public forms (3 steps each) for recruit/reactivate/activate with Back/Continue preserving answers"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/funnels/FunnelStepForm.jsx, funnelConfig.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Step X of 3 + progress bar, per-step validation, Back preserves answers. Recruitment submit navigates directly to /recruit/options (no result page); reactivation/activation keep their result pages."
  - task: "Recruitment options page with new offers and 'Program Access Opening Soon' gating"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/funnels/FunnelOptionsPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "New $97/$497/$3497 copy and include lists. Buttons disabled with 'Program Access Opening Soon' when flags false. ?internal=true enables TEST MODE checkout (requires admin cookie)."
  - task: "Member auth pages, purchase success account creation, dashboard, $97 and $497 course UIs with support box"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/member/*.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Routes: /purchase/success, /login, /forgot-password, /reset-password/:token, /app, /app/recruitment/basic[/module/:n], /app/recruitment/self-guided[/module/:n]. Video placeholder 'Training Video Coming Soon', Previous/Next/Mark Complete, support box on every module."

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 1
  run_ui: true

test_plan:
  current_focus:
    - "Recruitment funnel lead API with new 3-step question schema"
    - "Payment config + checkout gating with RECRUITMENT_97_LIVE/RECRUITMENT_497_LIVE flags and /purchase/success redirect"
    - "Member authentication (register/login/logout/me/forgot-password/reset-password)"
    - "Purchase claim with server-side Stripe verification and entitlements"
    - "Course APIs with entitlement enforcement, video config, progress tracking"
    - "Support requests saved and emailed to owner"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Phase 2 build complete. Please test backend per current_focus. Admin creds in /app/memory/test_credentials.md. Live purchase flags must stay FALSE — for checkout tests use internal_test:true with admin auth (Bearer or cookie). Stripe checkout sessions cannot be completed via API; verify claim-purchase returns 402 for unpaid sessions, and test entitlement access control by inserting entitlements directly into db.members. Do NOT modify Board Applicant Network. Do NOT flip env flags."

## PHASE 3 (appended by main agent)
backend:
  - task: "Module 1 recruitment profile API (get/save/confirm with lead prefill)"
    implemented: true
    working: "NA"
    file: "/app/backend/workspace_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET/PUT /api/workspace/profile (PUT unsets confirmed), POST /api/workspace/profile/confirm. Prefill from recruitment funnel lead."
  - task: "Claude generation endpoint with structured outputs, versioning, no auto-regeneration"
    implemented: true
    working: "NA"
    file: "/app/backend/workspace_routes.py, ai_service.py, workspace_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/workspace/generate (requires confirmed profile; per-application types require owned application_id). 18 generation types with fixed JSON schemas. Saves input/output/date/type/user/module/status in generated_materials with versions. GET/PUT materials, set current version. Manually verified one Claude call returns valid structured JSON."
  - task: "Opportunity lifecycle: application form editing, publish with duplicate-broadcast protection, close, test-mode broadcast"
    implemented: true
    working: "NA"
    file: "/app/backend/workspace_routes.py, opportunity_emails.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/workspace/opportunity, PUT /opportunity/application, POST /opportunity/publish (requires strategy+opportunity+application; atomic broadcast_initiated guard; test mode emails OWNER_TEST_EMAIL only), POST /opportunity/close."
  - task: "Public application endpoints: hosted apply, saved-profile tokens, receipt emails, auto interview guide"
    implemented: true
    working: "NA"
    file: "/app/backend/public_opportunity_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET/POST /api/public/board-opportunities/{slug}[/apply] (core question validation, CV GridFS, duplicate prevention by email, receipt email, background one-attempt interview guide), GET/POST /api/public/apply/{token} confirm + apply-updated (+optional profile update)."
  - task: "Applicant workspace: list/detail/status/notes/references/background-check/CV download/guide retry"
    implemented: true
    working: "NA"
    file: "/app/backend/workspace_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "All scoped to owner_user_id (tenant isolation). Statuses Applied/Reviewing/Interview/Selected/Not Selected/Withdrawn."
  - task: "E-signature workflow: prepare immutable snapshot, send, public sign, confirmations, signed download"
    implemented: true
    working: "NA"
    file: "/app/backend/workspace_routes.py, public_opportunity_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "POST /api/workspace/signatures/prepare (Selected only), /send (email link), GET/POST /api/public/sign/{token}, download at /api/workspace/signatures/{id}/download."

frontend:
  - task: "Phase 3 workspace UI in self-guided modules 1-6 + materials library + public apply/sign pages"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/member/workspace/*, /app/frontend/src/public/OpportunityPages.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Module1 5-step form+summary+confirm, Module2 strategy MaterialCard, Module3 six generators+application editor+publish panel, Module4 applicant workspace, Module5 references, Module6 selected-only onboarding+signatures. Routes: /app/recruitment/self-guided/materials, /board-opportunities/:slug/apply, /apply/:token, /sign/:token. Phase 2 video/nav/progress/support box preserved."

agent_communication:
  - agent: "main"
    message: "Phase 3 built. Test per Phase 3 tasks. MUST NOT change env flags (BOARD_APPLICANT_OPPORTUNITY_EMAILS_LIVE=false, RECRUITMENT_497_LIVE=false). Create $497 test member by registering then setting entitlements in Mongo. Claude generations cost credits — generate each type at most once where feasible; strategy + opportunity + application_questions + interview guide are the critical ones. Clean up test data afterwards. Do NOT modify reactivation/activation or Board Applicant Network code."

## PHASE 4 (appended by main agent)
backend:
  - task: "Public blog APIs + Claude generation with validation, correction attempt, duplicate scheduled-post protection"
    implemented: true
    working: true
    file: "/app/backend/marketing_service.py, marketing_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "GET /api/blog/posts(?category)/{slug}. Admin POST /api/blog/generate {category, publish_now}. Validation: word count, em dash, banned phrases, stats claims, duplicate slug/title. Unique index category_key+scheduled_date. Owner alerts on failure."
      - working: true
        agent: "testing"
        comment: "✓ Blog generation tested successfully. Generated 3 posts (recruitment, reactivation, fundraising_activation) with Claude. All posts validated: word count 650-1200, no em dash, no banned phrases, correct CTAs (/recruit, /reactivate, /activate), excerpts present. Duplicate protection working (409 on same category+date). Public APIs working: GET /api/blog/posts returns posts sorted newest first, category filter works, nonexistent slug returns 404. Unauthenticated POST /api/blog/generate returns 401. 3 published blog posts kept in database for frontend verification."
  - task: "Lead nurture: segments, one-active-category rule, fixed Tuesday rotation, duplicate-week protection, purchase removal"
    implemented: true
    working: true
    file: "/app/backend/marketing_service.py, funnel_routes.py, member_routes.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "sync_lead_nurture on every funnel lead (latest offer wins, removed from other segments). 12 fixed templates (no Claude). run_weekly_nurture: unique nurture_sends key segment+scheduled_week, rotation only advances on success, test mode emails OWNER_TEST_EMAIL only. Admin POST /api/nurture/test-send, GET /api/nurture/status. stop_recruitment_nurture on verified recruitment purchase. Flags BLOG_AUTOMATION_ENABLED=false, LEAD_NURTURE_ENABLED=false."
      - working: true
        agent: "testing"
        comment: "✓ Lead nurture tested successfully. Enrollment working: created recruitment lead → nurture_contacts has active_offer_source='recruitment', then created reactivation lead with same email → updated to 'reactivation' (latest wins). Created fundraising_activation lead → active_offer_source='fundraising_activation'. Tuesday send working: POST /api/nurture/test-send sent all 3 segments with template 1, correct CTAs (/recruit/options, /reactivate/options, /activate/options), correct subject for recruitment template 1. Rotation: last_sent=1 for all segments. Duplicate protection working: second test-send skipped all segments with duplicate reason, rotation unchanged. Purchase removal working: registered member → simulated stop_recruitment_nurture → nurture_status='customer', active_offer_source=''. Board applicants excluded from nurture_contacts. GET /api/nurture/status shows blog_automation_enabled='false', lead_nurture_enabled='false'. Phase 3 preserved: workspace profile without auth returns 401, payment config shows recruitment_497_live=false."
frontend:
  - task: "Public /blog + /blog/:slug pages and compact homepage Latest Articles slider"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/BlogPages.jsx, LandingPage.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Blog list with category filters, article page with deterministic category CTA, homepage slider (max 6, prev/next/swipe, Read All Articles) placed before join-network section."
agent_communication:
  - agent: "main"
    message: "Phase 4 built. Test blog + nurture per PHASE 4 tasks. Claude blog generation costs credits: generate exactly one article per category (3 total). NEVER flip env flags. Nurture test sends go only to owner test email. Do not email live segments or Board Applicants. Clean up test leads/posts records afterwards EXCEPT keep the 3 published test blog posts for frontend verification."
  - agent: "testing"
    message: "Phase 4 backend testing complete. All tests passed. Blog generation and lead nurture working correctly. 3 published blog posts kept in database for frontend verification (recruitment, reactivation, fundraising_activation). Test data cleaned up. Env flags verified unchanged (BLOG_AUTOMATION_ENABLED=false, LEAD_NURTURE_ENABLED=false). Ready for frontend testing."

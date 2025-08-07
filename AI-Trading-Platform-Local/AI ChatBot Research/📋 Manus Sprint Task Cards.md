# 📋 Manus Sprint Task Cards

**Sprint Title:** AI Onboarding Integration & Staking Dashboard Prototypes  
**Sprint Duration:** 7–10 days  
**Owner:** Manus  
**Lead Contact:** Richard  

---

## ✅ TASK 1: Onboarding Routing & Navigation

**Objective:**  
Implement seamless navigation between the main dashboard and the onboarding wizard

**Deliverables:**
* `Dashboard → Onboarding → Completion → Dashboard` routing
* Deep linking support for re-entry at last step
* "Resume Onboarding" option on dashboard

**Dependencies:**
* Step metadata from AI team
* Wizard entry point (e.g., `/onboarding/start`)

**Technical Notes:**
* Use React Router for navigation management
* Implement route guards for incomplete onboarding
* Store last completed step in localStorage/sessionStorage

---

## ✅ TASK 2: State Management Integration

**Objective:**  
Persist onboarding state and user responses using Redux or React Context

**Deliverables:**
* Shared onboarding state store
* Autosave progress per step
* Resilient state recovery across sessions

**Dependencies:**
* Backend session ID API
* Step identifiers (step type or index)

**Technical Notes:**
* Implement onboarding reducer with step-by-step state
* Auto-save to backend after each step completion
* Handle network failures gracefully with retry logic

---

## ✅ TASK 3: Subscription Tier Gating & Upgrade Flow

**Objective:**  
Gate access to premium strategies during onboarding and offer upsell

**Deliverables:**
* Real-time subscription check logic
* Modal for "Upgrade to Access This Strategy"
* Tier badge labels on strategy options
* Usage tracking hook (optional)

**Dependencies:**
* Tier definitions + pricing tiers (already set by AI team)
* Strategy metadata indicating tier level

**Technical Notes:**
* Create subscription context provider
* Implement tier-based feature gating components
* Design upgrade modal with clear value proposition

---

## ✅ TASK 4: Mobile Optimization Pass

**Objective:**  
Ensure wizard UI is fully responsive and touch-optimized

**Deliverables:**
* Tailwind responsiveness audit
* Adjust layout of Experience, Risk, and Goal steps on small screens
* Improve slider/touch input controls
* Tap-target review (spacing & focus)

**Technical Notes:**
* Test on iOS Safari and Android Chrome
* Ensure minimum 44px touch targets
* Optimize slider components for mobile interaction

---

## ✅ TASK 5: Performance Optimization Pass

**Objective:**  
Improve onboarding wizard performance and reduce bundle size

**Deliverables:**
* Lazy load each wizard step as needed
* Remove unnecessary animation calls
* Audit for unneeded re-renders or prop drilling
* Linting pass & build analysis

**Technical Notes:**
* Implement React.lazy() for step components
* Use React.memo() for expensive components
* Optimize Framer Motion animations for performance

---

## 🚧 TASK 6: Mining & Staking UI Prototypes (Exploratory)

**Objective:**  
Develop mock UI components for future staking/mining dashboards

**Deliverables:**
* "Staking Pool Opt-In" page (mocked):
  * Profit % slider
  * Earnings projection card
  * Pool participation toggle
* "Mining Pool Dashboard" (mocked):
  * Coin selection dropdown
  * Mock daily rewards chart
  * Status badge (idle/mining/paused)

**Dependencies:**
* Placeholder JSONs from Richard (optional)
* Visual theme matches current dashboard

**Technical Notes:**
* Create reusable staking/mining components
* Use mock data for demonstration purposes
* Maintain consistent design system

---

## 🧪 TASK 7: Investor Demo Mode Support

**Objective:**  
Enable a read-only onboarding walkthrough for demos

**Deliverables:**
* Optional `demo=true` URL parameter
* Pre-filled wizard responses
* Disable submit, navigation triggers
* Demo banner overlay (optional)

**Technical Notes:**
* Create demo data fixtures
* Implement read-only mode for all interactive elements
* Add subtle demo indicators without disrupting UX

---

## 📊 Success Metrics

**Performance Targets:**
* Onboarding completion rate: >85%
* Mobile responsiveness: 100% across major devices
* Load time: <2 seconds for initial wizard load
* Bundle size: <500KB for wizard components

**Quality Targets:**
* Zero console errors in production
* Accessibility score: >90 (WCAG 2.1 AA)
* Cross-browser compatibility: Chrome, Safari, Firefox, Edge

---

## 🔗 Resources & Support

**From Richard/AI Team:**
* Complete wizard components (7/10 steps finished)
* Backend API documentation and examples
* State structure definitions for Redux/Context
* Mobile breakpoint specifications

**Coordination:**
* Daily standup sync on integration progress
* Shared Slack channel for real-time questions
* Code review process for quality assurance

---

## 📅 Timeline

**Week 1 (Days 1-3):**
* Tasks 1-3: Core integration functionality

**Week 1 (Days 4-5):**
* Tasks 4-5: Optimization and polish

**Week 2 (Days 6-7):**
* Tasks 6-7: Strategic extensions and demo features

**Buffer (Days 8-10):**
* Integration testing, bug fixes, final polish


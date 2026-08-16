import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import axios from "axios";
import { CalendarClock, CheckCircle2, Check, ShieldCheck, X } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";
import { SITE_CONTENT, boardRecruitmentProposalPageText } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const GuaranteeTermsModal = ({ close }) => {
  const [terms, setTerms] = useState("");
  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setTerms(response.data.terms)).catch(() => setTerms(""));
  }, []);
  return (
    <div className="guarantee-modal-overlay" onClick={close} data-testid="brp-guarantee-modal-overlay">
      <div className="guarantee-modal" onClick={(event) => event.stopPropagation()} data-testid="brp-guarantee-modal">
        <button className="guarantee-close" onClick={close} aria-label="Close" data-testid="brp-guarantee-modal-close"><X size={20} /></button>
        <h3>Guarantee Terms</h3>
        <p data-testid="brp-guarantee-terms-text">{terms || "Loading…"}</p>
      </div>
    </div>
  );
};

const STEP_TWO_POINTS = ["Skills", "Experience", "Professional background", "Interest in your mission", "Capacity to serve", "Alignment with the organization", "Potential contribution to the board"];

const STEP_THREE_POINTS = [
  "Their role as board members",
  "Their commitment to the organization",
  "What responsibility they are expected to take",
  "How they support the founder or executive director",
  "How they contribute their skills, relationships and experience",
  "How they participate in building and moving the organization forward",
];

const ONBOARDING_DOCUMENTS = ["Board Member Agreement", "Confidentiality Agreement", "Conflict of Interest Agreement", "Board Member Profile Form"];

export default function BoardRecruitmentProposalPage() {
  usePageMeta(...PAGE_META.boardRecruitmentProposal);
  const location = useLocation();
  const cancelled = new URLSearchParams(location.search).get("checkout") === "cancelled";
  const [guaranteeConfigured, setGuaranteeConfigured] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [ctaNotice, setCtaNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/recruitment-guarantee`).then((response) => setGuaranteeConfigured(Boolean(response.data.configured))).catch(() => {});
  }, []);

  const makePayment = async () => {
    setBusy(true);
    setCtaNotice("");
    try {
      const response = await axios.post(`${API}/payments/direct-project-checkout`, { origin_url: window.location.origin });
      window.location.href = response.data.checkout_url;
    } catch {
      setCtaNotice("We could not start checkout. Please try again in a moment.");
      setBusy(false);
    }
  };

  return (
    <FunnelLayout restrained>
      <main data-testid="brp-page">
        <section className="funnel-hero-banner brp-hero" data-testid="brp-hero">
          <p className="eyebrow" data-testid="brp-hero-eyebrow">{boardRecruitmentProposalPageText.boardRecruitmentProjectProposal}</p>
          <h1 data-testid="brp-headline">{SITE_CONTENT.recruitProposal.headline}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="brp-hero-intro">{boardRecruitmentProposalPageText.yourNonprofitShouldNotHave}</p>
          <i aria-hidden="true" />
        </section>

        <section className="brp-section brp-summary" data-testid="brp-summary-section">
          <h2 className="brp-section-title" data-testid="brp-summary-heading">Executive Summary</h2>
          <p data-testid="brp-summary-whether">{boardRecruitmentProposalPageText.whetherYouNeedOneNew}</p>
          <p className="brp-summary-objective" data-testid="brp-summary-objective">{boardRecruitmentProposalPageText.helpYouRecruitTheBoard}</p>
          <p data-testid="brp-summary-timeline-line">{boardRecruitmentProposalPageText.overTheNextTwoWeeks}</p>
        </section>

        <section className="brp-section" data-testid="brp-how-section">
          <h2 className="brp-section-title" data-testid="brp-how-heading">{boardRecruitmentProposalPageText.hereIsHowWeWill}</h2>

          <article className="brp-step-card" data-testid="brp-step-1">
            <div className="brp-step-number">1</div>
            <div className="brp-step-body">
              <h3>{boardRecruitmentProposalPageText.launchYourRecruitmentCampaign}</h3>
              <p>{boardRecruitmentProposalPageText.duringOurFirst30Minute}</p>
              <p>{boardRecruitmentProposalPageText.weWillLaunchYourRecruitment}</p>
              <p>{boardRecruitmentProposalPageText.theObjectiveIsToPut}<strong>{boardRecruitmentProposalPageText.youHavePeopleToChoose}</strong></p>
            </div>
          </article>

          <article className="brp-step-card" data-testid="brp-step-2">
            <div className="brp-step-number">2</div>
            <div className="brp-step-body">
              <h3>{boardRecruitmentProposalPageText.decideWhoYouWant}</h3>
              <p>{boardRecruitmentProposalPageText.asApplicationsBeginComingIn}</p>
              <p>{boardRecruitmentProposalPageText.weWillInviteThemIn}</p>
              <ul className="brp-list icon-list">
                {STEP_TWO_POINTS.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
              </ul>
              <p>{boardRecruitmentProposalPageText.ifYouNeedHelpWith}</p>
            </div>
          </article>

          <article className="brp-step-card" data-testid="brp-step-3">
            <div className="brp-step-number">3</div>
            <div className="brp-step-body">
              <h3>{boardRecruitmentProposalPageText.getYourBoardMembersUp}</h3>
              <p>{boardRecruitmentProposalPageText.onceYouHaveSelectedThe}</p>
              <p>{boardRecruitmentProposalPageText.recruitingSomebodyIsNotEnough}</p>
              <p>{boardRecruitmentProposalPageText.yourNewBoardMembersNeed}</p>
              <p>{boardRecruitmentProposalPageText.weWillHelpMakeSure}</p>
              <ul className="brp-list icon-list">
                {STEP_THREE_POINTS.map((point) => <li key={point}><Check size={16} aria-hidden="true" /><span>{point}</span></li>)}
              </ul>
              <p>{boardRecruitmentProposalPageText.weWillAlsoTakeThem}</p>
              <ul className="brp-list brp-list-strong">
                {ONBOARDING_DOCUMENTS.map((doc) => <li key={doc}><strong>{doc}</strong></li>)}
              </ul>
              <p>{boardRecruitmentProposalPageText.thisWayYouWillGather}</p>
            </div>
          </article>
        </section>

        <section className="brp-section brp-result" data-testid="brp-result-section">
          <h2 className="brp-section-title">The Result</h2>
          <p className="brp-result-headline" data-testid="brp-result-headline">{boardRecruitmentProposalPageText.inTwoWeeksYouWill}</p>
          <p>{boardRecruitmentProposalPageText.aBoardOfSkilledProfessionals}</p>
          <p>{boardRecruitmentProposalPageText.andBecauseYouParticipateIn}</p>
          <p><strong>{boardRecruitmentProposalPageText.youWillUnderstandHowThe}</strong></p>
          <p>{boardRecruitmentProposalPageText.plusYouWillNotHave}</p>
        </section>

        <section className="brp-section brp-timeline" data-testid="brp-timeline-section">
          <h2 className="brp-section-title">Project Timeline</h2>
          <p className="brp-timeline-value" data-testid="brp-timeline-value"><CalendarClock size={34} aria-hidden="true" /> 2 Weeks</p>
          <p className="brp-timeline-note">{boardRecruitmentProposalPageText.weAlsoUnderstandThatEvery}</p>
        </section>

        <section className="brp-section brp-investment" data-testid="brp-investment-section">
          <h2 className="brp-section-title">Your Investment</h2>
          <p className="brp-standard-price" data-testid="brp-reference-price"><s>$3,997</s></p>
          <p className="brp-discount-line" data-testid="brp-discount-line">{boardRecruitmentProposalPageText.butIfYouAreReady}</p>
          <p className="brp-today-price" data-testid="brp-today-price">TODAY: $1,997</p>
        </section>

        <section className="brp-section brp-guarantee" data-testid="brp-guarantee-section">
          <ShieldCheck className="rwr-guarantee-icon" size={40} aria-hidden="true" />
          <h2 className="brp-section-title" data-testid="brp-guarantee-heading">{SITE_CONTENT.shared.guaranteeHeading}</h2>
          <p data-testid="brp-guarantee-copy">{SITE_CONTENT.shared.guaranteePrefix}<strong>{SITE_CONTENT.shared.guaranteeStrong}</strong></p>
          {guaranteeConfigured && (
            <button type="button" className="link-button rwr-terms-link" onClick={() => setShowTerms(true)} data-testid="brp-guarantee-terms-link">View Guarantee Terms</button>
          )}
        </section>

        <section className="brp-section" data-testid="brp-after-payment-section">
          <h2 className="brp-section-title" data-testid="brp-after-payment-heading">{boardRecruitmentProposalPageText.whatHappensAfterYouMake}</h2>
          <p data-testid="brp-after-payment-copy">{boardRecruitmentProposalPageText.afterMakingPaymentYouWill}</p>
        </section>

        <section className="brp-section brp-final-cta" data-testid="brp-final-cta-section">
          <h2 className="brp-section-title" data-testid="brp-ready-heading">{boardRecruitmentProposalPageText.readyToBuildYourBoard}</h2>
          <p>{boardRecruitmentProposalPageText.youDoNotHaveTo}</p>
          <p><strong>{boardRecruitmentProposalPageText.letSGetTheRight}</strong></p>
          {cancelled && <p className="rwr-cta-notice" data-testid="brp-cancelled-notice">{boardRecruitmentProposalPageText.yourPaymentWasNotCompleted}</p>}
          <button type="button" className="button rwr-cta-button brp-cta-button" onClick={makePayment} disabled={busy} data-testid="brp-cta-button">{busy ? "Preparing Checkout…" : SITE_CONTENT.recruitProposal.cta}</button>
          {ctaNotice && <p className="rwr-cta-notice" data-testid="brp-cta-notice">{ctaNotice}</p>}
          <div>
            <Link className="button button-outline offer-cross-link" to="/recruit-your-board-yourself" data-testid="brp-diy-cross-link">{boardRecruitmentProposalPageText.preferToDoItBy}</Link>
          </div>
        </section>

        <TestimonialCarousel heading="See What Other Nonprofit Founders and Leaders Have Said" idPrefix="brp" />
      </main>
      {showTerms && <GuaranteeTermsModal close={() => setShowTerms(false)} />}
    </FunnelLayout>
  );
}

export const BoardRecruitmentProposalConfirmedPage = () => {
  const location = useLocation();
  const sessionId = new URLSearchParams(location.search).get("session_id") || "";
  const [state, setState] = useState(sessionId ? "checking" : "missing");

  useEffect(() => {
    if (!sessionId) return undefined;
    let attempts = 0;
    let timer;
    const poll = async () => {
      attempts += 1;
      try {
        const response = await axios.get(`${API}/payments/status/${sessionId}`);
        if (response.data.payment_status === "paid") {
          setState("paid");
          timer = setTimeout(() => window.location.replace(`/board-recruitment-intake?session_id=${sessionId}`), 1800);
          return;
        }
        if (["failed", "expired"].includes(response.data.payment_status)) { setState("failed"); return; }
      } catch { /* keep polling */ }
      if (attempts < 8) timer = setTimeout(poll, 2500);
      else setState("timeout");
    };
    poll();
    return () => clearTimeout(timer);
  }, [sessionId]);

  return (
    <FunnelLayout restrained>
      <main className="brp-confirm-page" data-testid="brp-confirm-page">
        {state === "checking" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-checking">
            <h1>Confirming Your Payment…</h1>
            <p>{boardRecruitmentProposalPageText.pleaseWaitWhileWeVerify}</p>
          </div>
        )}
        {state === "missing" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-missing">
            <h1>Missing Payment Details</h1>
            <p>{boardRecruitmentProposalPageText.weCouldNotFindA}</p>
            <Link className="button" to="/board-recruitment-proposal">{boardRecruitmentProposalPageText.returnToTheProposal}</Link>
          </div>
        )}
        {(state === "failed" || state === "timeout") && (
          <div className="brp-confirm-card" data-testid="brp-confirm-failed">
            <h1>{boardRecruitmentProposalPageText.weCouldNotConfirmYour}</h1>
            <p>{boardRecruitmentProposalPageText.ifYouCompletedThePayment}</p>
            <Link className="button" to="/board-recruitment-proposal">{boardRecruitmentProposalPageText.returnToTheProposal2}</Link>
          </div>
        )}
        {state === "paid" && (
          <div className="brp-confirm-card" data-testid="brp-confirm-paid">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Payment confirmed</p>
            <h1>{boardRecruitmentProposalPageText.tellMeAboutYourOrganization}</h1>
            <p>{boardRecruitmentProposalPageText.takingYouToAShort}</p>
            <a className="button" href={`/board-recruitment-intake?session_id=${sessionId}`} data-testid="brp-intake-link">Continue</a>
          </div>
        )}
      </main>
    </FunnelLayout>
  );
};

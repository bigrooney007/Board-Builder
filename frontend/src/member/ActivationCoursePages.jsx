import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { SupportBox, VideoBlock } from "./CoursePages";
import { BoardFixContinuation } from "./BoardFixContinuation"; // eslint-disable-line no-unused-vars
import { StepInstructions } from "./StepInstructions";
import { bufStep } from "./bufJourney";
import ActivationModule2 from "./ActivationModule2";
import ActivationModule3 from "./ActivationModule3";
import ActivationModule4 from "./ActivationModule4";
import ActivationModule5 from "./ActivationModule5";
import { activationContent, sharedCourseContent, activationCoursePagesText } from "../content/appContent";

const META = {
  key: "activation_self_guided",
  endpoint: "/courses/activation/self-guided",
  base: "/app/activation/self-guided",
  label: "Board Fundraising Activation — Self-Guided System",
};

const useActivationCourse = () => {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const load = React.useCallback(() => {
    memberApi.get(META.endpoint).then((response) => setCourse(response.data)).catch((err) => {
      if (err.response?.status === 401) navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      else if (err.response?.status === 403) setForbidden(true);
      else setError("We could not load this course.");
    });
  }, [navigate]);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`); return; }
    load();
  }, [loading, member, navigate, load]);
  return { course, error, forbidden, reload: load };
};

const ForbiddenCard = () => (
  <div className="member-card" data-testid="activation-course-forbidden">
    <h2>{sharedCourseContent.forbidden.heading}</h2>
    <p>{sharedCourseContent.forbidden.body}</p>
    <Link className="button" to="/app">{sharedCourseContent.forbidden.backButton}</Link>
  </div>
);

export const ActivationOverviewPage = () => {
  const { course, error, forbidden } = useActivationCourse();
  const { member } = useMemberAuth();
  const navigate = useNavigate();
  useEffect(() => { document.title = "Board Fundraising Activation | Nonprofit Board Builder"; }, []);
  useEffect(() => {
    if (member && !(member.entitlements || []).includes("board_fix_system")) navigate("/app/activation/start", { replace: true });
  }, [member, navigate]);
  return (
    <MemberShell>
      <main className="member-page" data-testid="activation-overview">
        <header className="member-page-heading">
          <p className="eyebrow">Board Fundraising Activation</p>
          <h1>{META.label}</h1>
          {course && <p data-testid="activation-progress-summary">{course.percent_complete}% complete · {course.modules_completed} of {course.modules.length} modules finished</p>}
          {course && <div className="dashboard-progress-bar"><i style={{ width: `${course.percent_complete}%` }} /></div>}
        </header>
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && (
          <>
            <div className="module-list">
              {course.modules.map((module) => (
                <Link className="module-list-item" to={`${META.base}/module/${module.number}`} key={module.number} data-testid={`activation-module-link-${module.number}`}>
                  {module.completed ? <CheckCircle2 className="module-done" size={21} /> : <Circle className="module-todo" size={21} />}
                  <div><span>Module {module.number}</span><h2>{module.title}</h2></div>
                  <ArrowRight size={17} />
                </Link>
              ))}
            </div>
          </>
        )}
      </main>
    </MemberShell>
  );
};

const ModuleShell = ({ moduleNumber }) => {
  if (moduleNumber === 1) {
    return (
      <section className="member-card" data-testid="activation-module1-training">
        <h2>{activationContent.module1.heading}</h2>
        <p>{activationContent.module1.body}</p>
      </section>
    );
  }
  if (moduleNumber === 2) {
    return <ActivationModule2 />;
  }
  if (moduleNumber === 3) {
    return <ActivationModule3 />;
  }
  if (moduleNumber === 4) {
    return <ActivationModule4 />;
  }
  return <ActivationModule5 />;
};

export const ActivationModulePage = () => {
  const { course, error, forbidden, reload } = useActivationCourse();
  const { member } = useMemberAuth();
  const { moduleNumber } = useParams();
  const navigate = useNavigate();
  const number = Number(moduleNumber);
  const [marking, setMarking] = useState(false);
  const module = course?.modules.find((item) => item.number === number);
  const buf = bufStep(member, "activation", number);

  useEffect(() => {
    if (module) document.title = `Module ${module.number} | ${module.title} | Nonprofit Board Builder`;
  }, [module]);

  useEffect(() => {
    if (!course || !module) return;
    memberApi.post("/courses/progress", { product: META.key, module_number: number, action: "viewed" }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course?.product, number]);

  const nextStep = async () => {
    setMarking(true);
    try {
      if (!module.completed) await memberApi.post("/courses/progress", { product: META.key, module_number: number, action: "completed" });
      navigate(buf ? buf.next : (number < course.modules.length ? `${META.base}/module/${number + 1}` : "/app/activation/self-guided/my-fundraising-board"));
    } catch { /* ignore */ }
    setMarking(false);
  };

  return (
    <MemberShell>
      <main className="member-page module-page" data-testid="activation-module-page">
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && !module && <div className="member-card" data-testid="activation-module-not-found"><h2>Module Not Found</h2><Link className="button" to={META.base}>{activationCoursePagesText.backToBoardFundraisingActivation}</Link></div>}
        {module && (
          <>
            <header className="member-page-heading">
              <Link className="module-breadcrumb" to={buf ? "/board-fix-roadmap" : META.base} data-testid="activation-module-back"><ArrowLeft size={15} /> {buf ? "Your Board Fix Journey" : META.label}</Link>
              <p className="eyebrow">{buf ? `Complete Board Fix — Step ${buf.stepNumber} of ${buf.totalSteps}` : `Module ${module.number} of ${course.modules.length}`}</p>
              <h1 data-testid="activation-module-title">{module.title}</h1>
            </header>
            <VideoBlock module={module} testPrefix={`activation-module-${module.number}`} placeholderTitle={activationContent.videoPlaceholder} />
            {number >= 2 && <StepInstructions stepKey={`activation-${number}`} />}
            <ModuleShell moduleNumber={number} />
            <div className="module-nav" data-testid="activation-module-navigation">
              {(buf || number > 1) ? (
                <button className="button button-back" onClick={() => navigate(buf ? buf.prev : `${META.base}/module/${number - 1}`)} data-testid="activation-previous-button"><ArrowLeft size={16} /> Previous Module</button>
              ) : <span />}
              {(buf || number < course.modules.length) ? (
                <button className="button" disabled={marking} onClick={nextStep} data-testid="activation-next-step-button">NEXT STEP <ArrowRight size={16} /></button>
              ) : (
                <p style={{ margin: 0, fontWeight: 700 }} data-testid="activation-completion-message">Your Board Fundraising Activation System is ready to execute.</p>
              )}
            </div>
            <SupportBox productKey={META.key} moduleNumber={number} supportTypes={course.support_types} />
          </>
        )}
      </main>
    </MemberShell>
  );
};

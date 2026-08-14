import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle, LayoutDashboard } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { SupportBox, VideoBlock } from "./CoursePages";
import ActivationModule2 from "./ActivationModule2";
import ActivationModule3 from "./ActivationModule3";
import ActivationModule4 from "./ActivationModule4";
import ActivationModule5 from "./ActivationModule5";

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
    <h2>This Program Is Not Included in Your Account</h2>
    <p>Your account does not include access to this program. If you believe this is a mistake, please contact us.</p>
    <Link className="button" to="/app">Back to My Board Builder</Link>
  </div>
);

export const ActivationOverviewPage = () => {
  const { course, error, forbidden } = useActivationCourse();
  useEffect(() => { document.title = "Board Fundraising Activation | Nonprofit Board Builder"; }, []);
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
            <section className="member-card" style={{ marginTop: 18 }} data-testid="activation-my-fundraising-board-preview">
              <p className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}><LayoutDashboard size={15} aria-hidden="true" /> After Module 5</p>
              <h2 style={{ margin: "6px 0" }}>My Fundraising Board</h2>
              <p style={{ margin: 0 }}>Your permanent fundraising dashboard — your adopted fundraising strategy, each Board Member's fundraising responsibilities and their individual Fundraising Portfolios live here once your plan is adopted.</p>
              <Link className="button" style={{ marginTop: 12 }} to="/app/activation/self-guided/my-fundraising-board" data-testid="activation-open-my-fundraising-board">OPEN MY FUNDRAISING BOARD</Link>
            </section>
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
        <h2>Prepare to Build a Fundraising Board</h2>
        <p>This module is training only. Watch the video above to understand how fundraising Board ownership is created, then mark this module complete and continue to Module 2 to begin initiating the fundraising planning process with your Board.</p>
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
  const { moduleNumber } = useParams();
  const navigate = useNavigate();
  const number = Number(moduleNumber);
  const [marking, setMarking] = useState(false);
  const module = course?.modules.find((item) => item.number === number);

  useEffect(() => {
    if (module) document.title = `Module ${module.number} | ${module.title} | Nonprofit Board Builder`;
  }, [module]);

  useEffect(() => {
    if (!course || !module) return;
    memberApi.post("/courses/progress", { product: META.key, module_number: number, action: "viewed" }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course?.product, number]);

  const markComplete = async () => {
    setMarking(true);
    try {
      await memberApi.post("/courses/progress", { product: META.key, module_number: number, action: module.completed ? "uncompleted" : "completed" });
      reload();
    } catch { /* ignore */ }
    setMarking(false);
  };

  return (
    <MemberShell>
      <main className="member-page module-page" data-testid="activation-module-page">
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && !module && <div className="member-card" data-testid="activation-module-not-found"><h2>Module Not Found</h2><Link className="button" to={META.base}>Back to Board Fundraising Activation</Link></div>}
        {module && (
          <>
            <header className="member-page-heading">
              <Link className="module-breadcrumb" to={META.base} data-testid="activation-module-back"><ArrowLeft size={15} /> {META.label}</Link>
              <p className="eyebrow">Module {module.number} of {course.modules.length}</p>
              <h1 data-testid="activation-module-title">{module.title}</h1>
            </header>
            <VideoBlock module={module} testPrefix={`activation-module-${module.number}`} placeholderTitle="Board Fundraising Activation Training Video Coming Soon" />
            <ModuleShell moduleNumber={number} />
            <div className="module-nav" data-testid="activation-module-navigation">
              <button className="button button-back" disabled={number <= 1} onClick={() => navigate(`${META.base}/module/${number - 1}`)} data-testid="activation-previous-button"><ArrowLeft size={16} /> Previous Module</button>
              <button className={`button ${module.completed ? "completed-button" : ""}`} disabled={marking} onClick={markComplete} data-testid="activation-mark-complete-button">
                {module.completed ? <><CheckCircle2 size={16} /> Module Completed</> : "Mark This Module Complete"}
              </button>
              <button className="button button-back" disabled={number >= course.modules.length} onClick={() => navigate(`${META.base}/module/${number + 1}`)} data-testid="activation-next-button">Next Module <ArrowRight size={16} /></button>
            </div>
            <SupportBox productKey={META.key} moduleNumber={number} supportTypes={course.support_types} />
          </>
        )}
      </main>
    </MemberShell>
  );
};

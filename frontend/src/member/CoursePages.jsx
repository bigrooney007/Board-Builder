import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle, FileText, FolderOpen, LifeBuoy, PlayCircle } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { Module1Profile } from "./workspace/Module1Profile";
import { Module3Launch } from "./workspace/WorkspaceModules";
import { recruitmentContent, sharedCourseContent, coursePagesText } from "../content/appContent";
import { Module4Applicants, Module5References, Module6Onboarding } from "./workspace/ApplicantModules";

const PRODUCT_META = {
  basic: { key: "recruitment_basic", endpoint: "/courses/recruitment/basic", base: "/app/recruitment/basic", label: "Board Recruitment — $97 Program" },
  "self-guided": { key: "recruitment_self_guided", endpoint: "/courses/recruitment/self-guided", base: "/app/recruitment/self-guided", label: "Board Recruitment — Self-Guided System" },
};

const embedUrl = (url) => {
  if (!url) return "";
  const watch = url.match(/[?&]v=([\w-]{6,})/);
  if (watch) return `https://www.youtube.com/embed/${watch[1]}`;
  const short = url.match(/youtu\.be\/([\w-]{6,})/);
  if (short) return `https://www.youtube.com/embed/${short[1]}`;
  if (url.includes("/embed/")) return url;
  return url;
};

const useCourse = (productSlug) => {
  const meta = PRODUCT_META[productSlug];
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");
  const [forbidden, setForbidden] = useState(false);
  const load = React.useCallback(() => {
    memberApi.get(meta.endpoint).then((response) => setCourse(response.data)).catch((err) => {
      if (err.response?.status === 401) navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      else if (err.response?.status === 403) setForbidden(true);
      else setError("We could not load this course.");
    });
  }, [meta.endpoint, navigate]);
  useEffect(() => {
    if (loading) return;
    if (!member) { navigate(`/login?next=${encodeURIComponent(window.location.pathname)}`); return; }
    load();
  }, [loading, member, navigate, load]);
  return { meta, course, error, forbidden, reload: load };
};

const ForbiddenCard = () => (
  <div className="member-card" data-testid="course-forbidden">
    <h2>{sharedCourseContent.forbidden.heading}</h2>
    <p>{sharedCourseContent.forbidden.body}</p>
    <Link className="button" to="/app">{sharedCourseContent.forbidden.backButton}</Link>
  </div>
);

export const VideoBlock = ({ module, testPrefix, placeholderTitle }) => {
  const src = embedUrl(module.youtube_url);
  return src ? (
    <div className="module-video" data-testid={`${testPrefix}-video-embed`}>
      <iframe src={src} title={module.title} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
    </div>
  ) : (
    <div className="module-video placeholder" data-testid={`${testPrefix}-video-placeholder`}>
      <PlayCircle size={38} />
      <h3>{placeholderTitle || "Training Video Coming Soon"}</h3>
      <p>{coursePagesText.theTrainingVideoForThis}</p>
    </div>
  );
};

export const SupportBox = ({ productKey, moduleNumber, supportTypes }) => {
  const [supportType, setSupportType] = useState("");
  const [message, setMessage] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setError("");
    if (!supportType) { setError("Please choose what you need help with."); return; }
    setBusy(true);
    try {
      const response = await memberApi.post("/support-requests", { product: productKey, module_number: moduleNumber, support_type: supportType, message });
      setConfirmation(response.data.message);
    } catch (err) { setError(err.response?.data?.detail || "We could not send your request. Please try again."); }
    setBusy(false);
  };
  return (
    <section className="support-box" data-testid="module-support-box">
      <div className="support-box-heading"><LifeBuoy size={22} /><h2>{coursePagesText.needHelpWithThisStep}</h2></div>
      <p>{coursePagesText.ifYouAreStuckNeed}</p>
      {confirmation ? (
        <p className="member-success" data-testid="support-confirmation">{confirmation}</p>
      ) : (
        <form onSubmit={submit}>
          <label className="field"><span>{coursePagesText.whatDoYouNeedHelp}<b>*</b></span>
            <select value={supportType} onChange={(event) => setSupportType(event.target.value)} data-testid="support-type-select">
              <option value="">Select one</option>
              {(supportTypes || []).map((option) => <option key={option} value={option}>{option}</option>)}
            </select>
          </label>
          <label className="field"><span>{coursePagesText.tellUsWhatYouNeed}<b>*</b></span>
            <textarea rows="4" value={message} onChange={(event) => setMessage(event.target.value)} required data-testid="support-message-textarea" />
          </label>
          {error && <p className="submit-error" data-testid="support-error">{error}</p>}
          <button className="button" type="submit" disabled={busy} data-testid="support-submit-button">{busy ? "Sending…" : "Request Support"}</button>
        </form>
      )}
    </section>
  );
};

export const CourseOverviewPage = ({ productSlug }) => {
  const { meta, course, error, forbidden } = useCourse(productSlug);
  useEffect(() => { document.title = "Board Recruitment | Nonprofit Board Builder"; }, []);
  return (
    <MemberShell>
      <main className="member-page" data-testid={`course-overview-${productSlug}`}>
        <header className="member-page-heading">
          <p className="eyebrow">Board Recruitment</p>
          <h1>{meta.label}</h1>
          {course && <p data-testid="course-progress-summary">{course.percent_complete}% complete · {course.modules_completed} of {course.modules.length} steps finished</p>}
          {course && <div className="dashboard-progress-bar"><i style={{ width: `${course.percent_complete}%` }} /></div>}
        </header>
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && productSlug === "self-guided" && (
          <Link className="module-list-item materials-link" to="/app/recruitment/self-guided/materials" data-testid="materials-library-link">
            <FolderOpen size={21} className="module-done" />
            <div><span>Workspace</span><h2>My Recruitment Materials</h2></div>
            <ArrowRight size={17} />
          </Link>
        )}
        {course && (
          <div className="module-list">
            {course.modules.map((module) => (
              <Link className="module-list-item" to={`${meta.base}/module/${module.number}`} key={module.number} data-testid={`module-link-${module.number}`}>
                {module.completed ? <CheckCircle2 className="module-done" size={21} /> : <Circle className="module-todo" size={21} />}
                <div><span>Step {module.number}</span><h2>{module.title}</h2></div>
                <ArrowRight size={17} />
              </Link>
            ))}
          </div>
        )}
      </main>
    </MemberShell>
  );
};

const BasicResources = ({ module }) => (
  <section className="module-resources" data-testid="module-resources">
    <h2>Module Resources</h2>
    {module.resources.map((resource) => (
      <details className="resource-item" key={resource.title} data-testid={`resource-${resource.title.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`}>
        <summary><FileText size={16} /> {resource.title}</summary>
        <p>{resource.content}</p>
        {resource.steps && <ol className="linkedin-steps" data-testid="linkedin-launch-steps">{resource.steps.map((step) => <li key={step}>{step}</li>)}</ol>}
      </details>
    ))}
  </section>
);

const SelfGuidedWorkspace = ({ moduleNumber }) => {
  if (moduleNumber === 1) {
    return (
      <section className="member-card" data-testid="module1-training-card">
        <h2>{recruitmentContent.module1.heading}</h2>
        <p>{recruitmentContent.module1.body}</p>
      </section>
    );
  }
  if (moduleNumber === 2) return <Module1Profile />;
  if (moduleNumber === 3) return <Module3Launch />;
  if (moduleNumber === 4) return <Module4Applicants />;
  if (moduleNumber === 5) return <Module5References />;
  return <Module6Onboarding />;
};

export const CourseModulePage = ({ productSlug }) => {
  const { meta, course, error, forbidden, reload } = useCourse(productSlug);
  const { moduleNumber } = useParams();
  const navigate = useNavigate();
  const number = Number(moduleNumber);
  const [marking, setMarking] = useState(false);
  const module = course?.modules.find((item) => item.number === number);

  useEffect(() => {
    if (module) document.title = `Step ${module.number} | ${module.title} | Nonprofit Board Builder`;
  }, [module]);

  useEffect(() => {
    if (!course || !module) return;
    memberApi.post("/courses/progress", { product: meta.key, module_number: number, action: "viewed" }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [course?.product, number]);

  const nextStep = async () => {
    setMarking(true);
    try {
      if (!module.completed) await memberApi.post("/courses/progress", { product: meta.key, module_number: number, action: "completed" });
      navigate(number < course.modules.length ? `${meta.base}/module/${number + 1}` : productSlug === "self-guided" ? "/app/recruitment/self-guided/results" : meta.base);
    } catch { /* ignore */ }
    setMarking(false);
  };

  return (
    <MemberShell>
      <main className="member-page module-page" data-testid={`course-module-page-${productSlug}`}>
        {forbidden && <ForbiddenCard />}
        {error && <p className="submit-error">{error}</p>}
        {course && !module && <div className="member-card"><h2>Module Not Found</h2><Link className="button" to={meta.base}>Back to Course</Link></div>}
        {module && (
          <>
            <header className="member-page-heading">
              <Link className="module-breadcrumb" to={meta.base} data-testid="module-back-to-course"><ArrowLeft size={15} /> {meta.label}</Link>
              <p className="eyebrow">Step {module.number} of {course.modules.length}</p>
              <h1 data-testid="module-title">{module.title}</h1>
            </header>
            <VideoBlock module={module} testPrefix={`module-${module.number}`} placeholderTitle={module.number === 1 ? "Board Recruitment Training Video Coming Soon" : undefined} />
            {productSlug === "basic" ? <BasicResources module={module} /> : <SelfGuidedWorkspace moduleNumber={number} />}
            <div className="module-nav" data-testid="module-navigation">
              <button className="button button-back" disabled={number <= 1} onClick={() => navigate(`${meta.base}/module/${number - 1}`)} data-testid="previous-module-button"><ArrowLeft size={16} /> Previous Step</button>
              <button className="button" disabled={marking} onClick={nextStep} data-testid="next-step-button">NEXT STEP <ArrowRight size={16} /></button>
            </div>
            <SupportBox productKey={meta.key} moduleNumber={number} supportTypes={course.support_types} />
          </>
        )}
      </main>
    </MemberShell>
  );
};

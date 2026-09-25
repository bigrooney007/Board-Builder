import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { ArrowRight, Users, Gamepad2, Map, RefreshCw, Handshake, UserRoundPlus } from "lucide-react";
import { FounderStorySection } from "@/components/FounderStorySection";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { BlogSlider } from "@/pages/BlogPages";
import { useHomepageContent } from "@/clean/platform";
import "./MainHomePage.css";

const PRODUCT_META = [
  { icon: Users, to: "/recruit", image: "https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=1200&q=80", imageAlt: "Professionals working together around a table" },
  { icon: Gamepad2, to: "/board-fundraising-game", image: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80", imageAlt: "A group collaborating together" },
  { icon: Map, to: "/strategic-planning", image: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80", imageAlt: "A team planning strategy together" },
  { icon: RefreshCw, to: "/board-recommitment", image: "https://images.unsplash.com/photo-1521791055366-0d553872125f?auto=format&fit=crop&w=1200&q=80", imageAlt: "Professionals recommitting through a handshake" },
  { icon: Handshake, to: "/organize-board-fundraising-game", image: "https://images.unsplash.com/photo-1517048676732-d65bc937f952?auto=format&fit=crop&w=1200&q=80", imageAlt: "A nonprofit board meeting with a facilitator" },
];

export const MAIN_HOME_DEFAULTS = {
  heroEyebrow: "NONPROFIT LEADERSHIP SYSTEMS",
  heroHeadline: "Build The Board And Systems Your Nonprofit Needs To Grow And Raise Money Exponentially.",
  heroLead: "Your nonprofit cannot grow beyond the people making the decisions and the systems helping them execute. We help you build stronger boards, activate them around fundraising and turn organizational priorities into strategy.",
  heroCta: "CHOOSE WHAT YOU NEED",
  problemIntro: "You do not need another expensive consultant.",
  problemHeading: "What you need is the right board members providing you the right kind of support.",
  problemText: "At Nonprofit Board Builders, our sole purpose is to equip you to build the exact type of board your organization needs so you can work with them to raise money exponentially and scale your organization.",
  pathsEyebrow: "CHOOSE YOUR PATH",
  pathsHeading: "What Does Your Organization Need Right Now?",
  products: [
    { eyebrow: "BUILD THE RIGHT BOARD", title: "Recruit The Board Members Your Organization Needs", text: "Identify the exact skills, experience and relationships your board needs, then launch a professional recruitment campaign to find and bring the right people onto your board.", cta: "START BOARD RECRUITMENT" },
    { eyebrow: "GET YOUR BOARD RAISING MONEY", title: "Turn Your Board Into An Active Fundraising Team", text: "Use the Board Fundraising Game to help your board think strategically about fundraising, build the fundraising system together and leave with clear individual roles for execution.", cta: "PLAY THE BOARD FUNDRAISING GAME" },
    { eyebrow: "ALIGN YOUR ORGANIZATION", title: "Build A Strategic Plan Your Team Can Actually Execute", text: "Bring your people into the planning process, turn their perspectives into clear priorities and move from ideas to an actionable organizational strategy.", cta: "EXPLORE STRATEGIC PLANNING" },
    { eyebrow: "GET YOUR BOARD TO RECOMMIT", title: "Get Your Present Board Members To Step Up Again", text: "Help your present board members recommit to their responsibilities, clarify how they want to contribute and identify who is genuinely ready to keep building the organization with you.", cta: "EXPLORE BOARD RECOMMITMENT" },
    { eyebrow: "FACILITATED WITH ROONEY", title: "Let Us Organize And Facilitate Your Board Fundraising Game", text: "Apply to have Rooney organize the process, prepare your board and facilitate the Board Fundraising Game with your organization.", cta: "APPLY FOR THE FACILITATED GAME" },
  ],
  testimonialsHeading: "What Nonprofit Leaders We Have Worked With Are Saying",
  applicantEyebrow: "SERVE ON A NONPROFIT BOARD",
  applicantTitle: "Join The Board Applicant Network",
  applicantText: "Create your Board Applicant profile once and make your skills, experience, causes and availability visible for nonprofit board opportunities that match how you want to serve.",
  applicantCta: "JOIN THE BOARD APPLICANT NETWORK",
  closingHeading: "Stop Building Around Whoever Happens To Be Available.",
  closingText: "Build intentionally around what your mission actually needs. If you are looking to serve, join the Board Applicant Network and make yourself available to nonprofits looking for the right Board Members.",
  closingCta: "CHOOSE MY PATH",
  closingApplicantCta: "JOIN THE BOARD APPLICANT NETWORK",
};

export default function MainHomePage() {
  const navigate = useNavigate();
  const copy = useHomepageContent("main", MAIN_HOME_DEFAULTS);
  const { member, loading, logout } = useMemberAuth();
  const handleLogout = async () => { await logout(); navigate("/login"); };

  return (
    <div className="nBB-home">
      <header className="nBB-home-nav" style={{ justifyContent: "flex-end" }}>
        {!loading && (member ? (
          <button type="button" className="nBB-home-login" onClick={handleLogout} data-testid="home-logout-button">LOG OUT</button>
        ) : (
          <Link to="/login" className="nBB-home-login" data-testid="home-login-button">LOG IN</Link>
        ))}
      </header>
      <main>
        <section className="nBB-home-hero">
          <p className="nBB-home-eyebrow">{copy.heroEyebrow}</p>
          <h1>{copy.heroHeadline}</h1>
          <p className="nBB-home-lead">{copy.heroLead}</p>
          <a href="#choose-path" className="nBB-home-primary">{copy.heroCta} <ArrowRight size={18}/></a>
        </section>

        <section className="nBB-home-problem">
          <p>{copy.problemIntro}</p>
          <h2>{copy.problemHeading}</h2>
          <p>{copy.problemText}</p>
        </section>

        <section id="choose-path" className="nBB-home-paths">
          <div className="nBB-home-section-head">
            <p className="nBB-home-eyebrow">{copy.pathsEyebrow}</p>
            <h2>{copy.pathsHeading}</h2>
          </div>
          <div className="nBB-home-grid">
            {(copy.products || MAIN_HOME_DEFAULTS.products).map((product, index) => {
              const meta = PRODUCT_META[index] || PRODUCT_META[0];
              const Icon = meta.icon;
              return <article key={meta.to} className="nBB-home-card">
                <img src={meta.image} alt={meta.imageAlt} loading="lazy" />
                <div className="nBB-home-card-body">
                  <Icon size={30}/>
                  <p className="nBB-home-eyebrow">{product.eyebrow}</p>
                  <h3>{product.title}</h3>
                  <p>{product.text}</p>
                  <Link className="nBB-home-card-button" to={meta.to}>{product.cta} <ArrowRight size={17}/></Link>
                </div>
              </article>;
            })}
            <article className="nBB-home-card" data-testid="home-board-applicant-network">
              <img
                src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1200&q=80"
                alt="Professionals bringing different skills together around a shared mission"
                loading="lazy"
              />
              <div className="nBB-home-card-body">
                <UserRoundPlus size={30}/>
                <p className="nBB-home-eyebrow">{copy.applicantEyebrow || MAIN_HOME_DEFAULTS.applicantEyebrow}</p>
                <h3>{copy.applicantTitle || MAIN_HOME_DEFAULTS.applicantTitle}</h3>
                <p>{copy.applicantText || MAIN_HOME_DEFAULTS.applicantText}</p>
                <Link className="nBB-home-card-button" to="/join-a-board" data-testid="home-join-board-network-button">
                  {copy.applicantCta || MAIN_HOME_DEFAULTS.applicantCta} <ArrowRight size={17}/>
                </Link>
              </div>
            </article>
          </div>
        </section>

        <section className="nBB-home-founder-wrap"><FounderStorySection /></section>
        <section className="nBB-home-proof"><TestimonialCarousel heading={copy.testimonialsHeading} idPrefix="home" /></section>
        <section className="nBB-home-blog"><BlogSlider /></section>

        <section className="nBB-home-closing">
          <h2>{copy.closingHeading}</h2>
          <p>{copy.closingText}</p>
          <div className="nBB-home-closing-actions">
            <a href="#choose-path" className="nBB-home-primary">{copy.closingCta} <ArrowRight size={18}/></a>
            <Link to="/join-a-board" className="nBB-home-primary nBB-home-secondary-cta" data-testid="home-closing-join-board-network">
              {copy.closingApplicantCta || MAIN_HOME_DEFAULTS.closingApplicantCta} <ArrowRight size={18}/>
            </Link>
          </div>
        </section>
      </main>
      <footer className="nBB-home-footer">
        <span>© {new Date().getFullYear()} Nonprofit Board Builder</span>
        <Link to="/privacy-policy">Privacy</Link>
        <Link to="/terms">Terms</Link>
      </footer>
    </div>
  );
}

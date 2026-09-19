import { Link } from "react-router-dom";
import { ArrowRight, Users, Gamepad2, Map, RefreshCw } from "lucide-react";
import { FounderStorySection } from "@/components/FounderStorySection";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { BlogSlider } from "@/pages/BlogPages";
import "./MainHomePage.css";

const products = [
  {
    icon: Users,
    eyebrow: "BUILD THE RIGHT BOARD",
    title: "Recruit The Board Members Your Organization Needs",
    text: "Identify the exact skills, experience and relationships your board needs, then launch a professional recruitment campaign to find and bring the right people onto your board.",
    cta: "START BOARD RECRUITMENT",
    to: "/recruit",
    image: "https://images.unsplash.com/photo-1521737711867-e3b97375f902?auto=format&fit=crop&w=1200&q=80",
    imageAlt: "Professionals working together around a table",
  },
  {
    icon: Gamepad2,
    eyebrow: "GET YOUR BOARD RAISING MONEY",
    title: "Turn Your Board Into An Active Fundraising Team",
    text: "Use the Board Fundraising Game to help your board think strategically about fundraising, build the fundraising system together and leave with clear individual roles for execution.",
    cta: "PLAY THE BOARD FUNDRAISING GAME",
    to: "/board-fundraising-game",
    image: "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1200&q=80",
    imageAlt: "A group collaborating together",
  },
  {
    icon: Map,
    eyebrow: "ALIGN YOUR ORGANIZATION",
    title: "Build A Strategic Plan Your Team Can Actually Execute",
    text: "Bring your people into the planning process, turn their perspectives into clear priorities and move from ideas to an actionable organizational strategy.",
    cta: "EXPLORE STRATEGIC PLANNING",
    to: "/strategic-planning",
    image: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?auto=format&fit=crop&w=1200&q=80",
    imageAlt: "A team planning strategy together",
  },
  {
    icon: RefreshCw,
    eyebrow: "GET YOUR BOARD TO RECOMMIT",
    title: "Get Your Present Board Members To Step Up Again",
    text: "Help your present board members recommit to their responsibilities, clarify how they want to contribute and identify who is genuinely ready to keep building the organization with you.",
    cta: "EXPLORE BOARD RECOMMITMENT",
    to: "/board-recommitment",
    image: "https://images.unsplash.com/photo-1521791055366-0d553872125f?auto=format&fit=crop&w=1200&q=80",
    imageAlt: "Professionals recommitting through a handshake",
  },
];

export default function MainHomePage() {
  return (
    <div className="nBB-home">
      <header className="nBB-home-nav">
        <Link to="/" className="nBB-home-brand">
          <span>NB</span>
          <div><strong>NONPROFIT BOARD BUILDER</strong><small>Build the board. Build the strategy. Build the organization.</small></div>
        </Link>
        <Link to="/login" className="nBB-home-login">LOGIN</Link>
      </header>
      <main>
        <section className="nBB-home-hero">
          <p className="nBB-home-eyebrow">NONPROFIT LEADERSHIP SYSTEMS</p>
          <h1>Build The Board And Systems Your Nonprofit Needs To Grow And Raise Money Exponentially.</h1>
          <p className="nBB-home-lead">Your nonprofit cannot grow beyond the people making the decisions and the systems helping them execute. We help you build stronger boards, activate them around fundraising and turn organizational priorities into strategy.</p>
          <a href="#choose-path" className="nBB-home-primary">CHOOSE WHAT YOU NEED <ArrowRight size={18}/></a>
        </section>

        <section className="nBB-home-problem">
          <p>Most nonprofit leaders do not need another collection of templates.</p>
          <h2>They need the right people, a clear plan and a system that gets everyone moving in the same direction.</h2>
          <p>That is what Nonprofit Board Builder is designed to help you build.</p>
        </section>

        <section id="choose-path" className="nBB-home-paths">
          <div className="nBB-home-section-head">
            <p className="nBB-home-eyebrow">CHOOSE YOUR PATH</p>
            <h2>What Does Your Organization Need Right Now?</h2>
          </div>
          <div className="nBB-home-grid">
            {products.map(({ icon: Icon, ...p }) => (
              <article key={p.to} className="nBB-home-card">
                <img src={p.image} alt={p.imageAlt} loading="lazy" />
                <div className="nBB-home-card-body">
                  <Icon size={30}/>
                  <p className="nBB-home-eyebrow">{p.eyebrow}</p>
                  <h3>{p.title}</h3>
                  <p>{p.text}</p>
                  <Link className="nBB-home-card-button" to={p.to}>{p.cta} <ArrowRight size={17}/></Link>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="nBB-home-founder-wrap">
          <FounderStorySection />
        </section>

        <section className="nBB-home-proof">
          <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix="home" />
        </section>

        <section className="nBB-home-blog">
          <BlogSlider />
        </section>

        <section className="nBB-home-closing">
          <h2>Stop Building Around Whoever Happens To Be Available.</h2>
          <p>Build intentionally around what your mission actually needs.</p>
          <a href="#choose-path" className="nBB-home-primary">CHOOSE MY PATH <ArrowRight size={18}/></a>
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

import { useEffect } from "react";

const setMeta = (attr, name, content) => {
  let el = document.head.querySelector(`meta[${attr}="${name}"]`);
  if (!el) { el = document.createElement("meta"); el.setAttribute(attr, name); document.head.appendChild(el); }
  el.setAttribute("content", content);
};

export const usePageMeta = (title, description, noindex = false) => {
  useEffect(() => {
    if (title) {
      document.title = title;
      setMeta("property", "og:title", title);
      setMeta("name", "twitter:title", title);
    }
    if (description) {
      setMeta("name", "description", description);
      setMeta("property", "og:description", description);
      setMeta("name", "twitter:description", description);
    }
    if (noindex) {
      setMeta("name", "robots", "noindex");
      return () => {
        const el = document.head.querySelector('meta[name="robots"]');
        if (el) el.remove();
      };
    }
    return undefined;
  }, [title, description, noindex]);
};

export const PAGE_META = {
  home: ["Nonprofit Board Builder | Build the Board Your Mission Deserves", "Build a stronger nonprofit board with committed people who can help raise money, strengthen your organization and move your mission forward. Recruit, reactivate and activate your board with Nonprofit Board Builder."],
  recruitment: ["Recruit Nonprofit Board Members | Nonprofit Board Builder", "Start recruiting committed, capable board members with the skills, experience, relationships and fundraising capacity your nonprofit needs to move forward."],
  process: ["Build the Board Your Nonprofit Needs | Nonprofit Board Builder", "See the six stages for building a committed nonprofit board that strengthens your organization, supports fundraising and helps move your mission forward."],
  checkout: ["Guided Board Recruitment | Nonprofit Board Builder", "Get the guidance, resources and support you need to recruit committed, capable board members and build the stronger board your nonprofit needs."],
  recruitWithRooney: ["Recruit With Rooney | Nonprofit Board Builder", "Recruit the board members your nonprofit needs with direct guidance and support from Rooney Akpesiri."],
  boardRecruitmentProposal: ["Board Recruitment Project Proposal | Nonprofit Board Builder", "Work directly with Rooney to recruit and onboard the skilled board members your nonprofit needs."],
  aboutRooney: ["Rooney Akpesiri | The Nonprofit Board Builder", "Helping nonprofits build strong fundraising board. Discover the two ways Rooney can help you recruit the board your nonprofit needs."],
  recruitYourBoardYourself: ["Recruit Your Board Yourself | Nonprofit Board Builder", "Follow Rooney's board recruitment process, use the execution materials provided and recruit the board members your nonprofit needs."],
  boardRecruitmentIntake: ["Tell Me About Your Organization and Board | Nonprofit Board Builder", "Provide the information needed to begin your board recruitment engagement."],
  reactivation: ["Reactivate Your Nonprofit Board | Nonprofit Board Builder", "Help committed board members step up, give inactive members a respectful path to step down and rebuild an engaged board ready to move your nonprofit forward."],
  fundraising_activation: ["Activate Your Board to Raise Money | Nonprofit Board Builder", "Activate your nonprofit board around fundraising so members use their strengths, relationships and experience to help raise money and strengthen your organization."],
  blog: ["Nonprofit Board Recruitment, Reactivation & Fundraising | Nonprofit Board Builder", "Practical insights for nonprofit founders and executive directors who want to recruit stronger board members, reactivate their present board and get their board involved in fundraising."],
};

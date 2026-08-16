import { BriefcaseBusiness, CalendarDays, Check, FileText, MapPin, Users } from "lucide-react";
import { productToolsSectionText } from "../content/siteContent";

const prospects = [
  ["Dr. Angela Morris", "Community Pediatrician", "Child health and community partnerships", "Corporate introductions", "Birmingham, Alabama", "Interview Scheduled"],
  ["Marcus Reynolds", "Regional Banking Executive", "Finance and community investment", "Business partnerships", "Birmingham, Alabama", "Application Received"],
  ["Jasmine Carter", "Marketing and Communications Director", "Brand development and public relations", "Campaign promotion", "Hoover, Alabama", "Under Review"],
  ["David Collins", "Attorney", "Nonprofit law and governance", "Professional network", "Birmingham, Alabama", "Invited to Apply"],
];

const ToolFrame = ({ number, title, caption, children }) => (
  <article className="tool-showcase" data-testid={`sample-tool-${number}`}>
    <div className="tool-frame">
      <div className="app-bar"><div className="app-dots"><i /><i /><i /></div><span data-testid={`sample-label-${number}`}>Sample</span></div>
      {children}
    </div>
    <div className="tool-caption"><span>0{number}</span><div><h3 data-testid={`sample-tool-title-${number}`}>{title}</h3><p data-testid={`sample-tool-caption-${number}`}>{caption}</p></div></div>
  </article>
);

const MockField = ({ label, value = "", wide = false }) => <div className={`mock-field ${wide ? "wide" : ""}`}><span>{label}</span><div>{value}</div></div>;
const MockOption = ({ selected, children }) => <div className="mock-option"><i className={selected ? "selected" : ""}>{selected && <Check size={10} />}</i><span>{children}</span></div>;

export const ProductToolsSection = () => (
  <section id="tools-materials" className="tools-section" data-testid="product-tools-section">
    <div className="tools-heading">
      <p className="eyebrow light" data-testid="tools-eyebrow">{productToolsSectionText.toolsBuiltForExecution}</p>
      <h2 data-testid="tools-heading">{productToolsSectionText.weGiveYouTheStrategy}</h2>
      <p data-testid="tools-supporting-text">{productToolsSectionText.youWillNotBeLeft}</p>
    </div>
    <div className="tools-list">
      <ToolFrame number={1} title={productToolsSectionText.boardProspectList} caption="Identify and organize qualified board prospects based on the exact skills, experience and fundraising capacity your board is missing.">
        <div className="mock-app prospect-app" data-testid="board-prospect-list-screenshot">
          <div className="mock-app-header"><div><span className="mock-kicker">{productToolsSectionText.brightFuturesLiteracyInitiative}</span><h3>Board Prospect List</h3></div><span className="mock-action" data-testid="sample-add-prospect-control">+ Add Prospect</span></div>
          <div className="prospect-table">
            <div className="prospect-row prospect-head"><span>Name / Profession</span><span>Board skills</span><span>Fundraising strength</span><span>Location</span><span>Application status</span></div>
            {prospects.map((prospect, index) => <div className="prospect-row" key={prospect[0]} data-testid={`sample-prospect-${index + 1}`}><span><strong>{prospect[0]}</strong><small>{prospect[1]}</small></span><span>{prospect[2]}</span><span>{prospect[3]}</span><span><MapPin size={11} />{prospect[4]}</span><span><b>{prospect[5]}</b></span></div>)}
          </div>
        </div>
      </ToolFrame>

      <ToolFrame number={2} title={productToolsSectionText.applyToJoinOurBoard2} caption="Attract serious applicants and collect the information required to determine who can genuinely strengthen your board.">
        <div className="mock-app form-mock" data-testid="board-application-form-screenshot">
          <div className="form-mock-banner"><div><span className="mock-kicker">{productToolsSectionText.brightFuturesLiteracyInitiative2}</span><h3>{productToolsSectionText.applyToJoinOurBoard}</h3><p>{productToolsSectionText.helpExpandLiteracyAccessFor}</p></div><Users size={35} /></div>
          <div className="mock-fields compact-grid"><MockField label="Full name" /><MockField label="Email" /><MockField label="Phone" /><MockField label="Profession" /><MockField label="Current organization" /><MockField label="Previous board experience" /><MockField label="Why do you want to join this board?" wide /><MockField label="Which skills and experience would you bring?" wide /><MockField label="Which fundraising activities are you willing to support?" wide /><MockField label="Which professional or community relationships could help the mission?" wide /><MockField label="How many hours can you commit each month?" /><MockField label="Are you willing to attend meetings consistently?" /><MockField label="Are you willing to take responsibility for agreed assignments?" /><MockField label="Upload résumé" value="Choose file" /></div>
          <span className="mock-submit" data-testid="sample-board-application-submit-control">Submit Board Application</span>
        </div>
      </ToolFrame>

      <ToolFrame number={3} title={productToolsSectionText.boardFundraisingPlanningForm2} caption="Activate every board member around the fundraising activities that fit their strengths, experience and relationships.">
        <div className="mock-app planning-mock" data-testid="fundraising-planning-form-screenshot">
          <div className="mock-app-header"><div><span className="mock-kicker">{productToolsSectionText.boardMemberMarcusReynolds}</span><h3>{productToolsSectionText.boardFundraisingPlanningForm}</h3></div><BriefcaseBusiness size={30} /></div>
          <div className="planning-grid"><div className="planning-question"><strong>{productToolsSectionText.whichFundraisingAreasAreYou}</strong><MockOption selected>Corporate introductions</MockOption><MockOption selected>Sponsorship conversations</MockOption><MockOption selected>Reviewing partnership proposals</MockOption></div><div className="planning-question"><strong>{productToolsSectionText.whichPeopleOrBusinessesCould}</strong><p>{productToolsSectionText.regionalBanksLocalAccountingFirms}</p></div><div className="planning-question"><strong>{productToolsSectionText.whichPartOfTheFundraising}</strong><p>{productToolsSectionText.helpIdentifyTenLocalCorporate}</p></div><div className="planning-question"><strong>{productToolsSectionText.whatSupportOrMaterialsDo}</strong><p>{productToolsSectionText.corporatePartnershipOverviewEmailIntroduction}</p></div><div className="planning-question date-question"><CalendarDays size={18} /><div><strong>{productToolsSectionText.whenWillYouBegin}</strong><p>September 15</p></div></div></div>
        </div>
      </ToolFrame>

      <ToolFrame number={4} title={productToolsSectionText.boardRecommitmentAndPlanningForm2} caption="Give present board members a clear opportunity to recommit, accept meaningful responsibility or step down respectfully.">
        <div className="mock-app recommitment-mock" data-testid="board-recommitment-form-screenshot">
          <div className="mock-app-header"><div><span className="mock-kicker">{productToolsSectionText.brightFuturesLiteracyInitiative3}</span><h3>{productToolsSectionText.boardRecommitmentAndPlanningForm}</h3></div><FileText size={30} /></div>
          <div className="recommitment-grid"><div className="planning-question"><strong>{productToolsSectionText.doYouRemainCommittedTo}</strong><MockOption selected>{productToolsSectionText.yesIAmFullyCommitted}</MockOption><MockOption>{productToolsSectionText.iNeedMoreInformationBefore}</MockOption><MockOption>{productToolsSectionText.iAmNoLongerAble}</MockOption></div><div className="planning-question"><strong>{productToolsSectionText.canYouAttendScheduledBoard}</strong><MockOption selected>Yes</MockOption><MockOption>No</MockOption><MockOption>With advance notice</MockOption></div><div className="planning-question wide-question"><strong>{productToolsSectionText.whichAreasAreYouWilling}</strong><div className="tag-cloud">{["Governance", "Fundraising", "Community outreach", "Corporate partnerships", "Volunteer recruitment", "Marketing", "Program support", "Financial oversight"].map((tag, index) => <span className={index === 1 || index === 3 ? "active" : ""} key={tag}>{tag}</span>)}</div></div><div className="planning-question"><strong>{productToolsSectionText.whichResponsibilityAreYouPrepared}</strong><p>{productToolsSectionText.helpBuildRelationshipsWithLocal}</p></div><div className="planning-question"><strong>{productToolsSectionText.whatSupportDoYouNeed}</strong><p>{productToolsSectionText.clearExpectationsQuarterlyTargetsAnd}</p></div><div className="planning-question wide-question"><strong>Recommitment decision</strong><MockOption selected>{productToolsSectionText.iRecommitForTheNext}</MockOption><MockOption>{productToolsSectionText.iWouldLikeToDiscuss}</MockOption><MockOption>{productToolsSectionText.iAmReadyToStep}</MockOption></div></div>
          <span className="mock-submit" data-testid="sample-recommitment-submit-control">{productToolsSectionText.submitMyRecommitmentDecision}</span>
        </div>
      </ToolFrame>
    </div>
  </section>
);
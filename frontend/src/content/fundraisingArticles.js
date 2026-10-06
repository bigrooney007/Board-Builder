/* eslint-env node */
// These public guides are versioned with the application and need no account or database record.
const START_PATH = "/board-fundraising/start";
const CTA = "Answer the 5 fundraising questions and get my board fundraising";
const articles = [
  {
    slug: "three-steps-to-get-your-board-fundraising",
    title: "Three steps to get your board members raising money by your next board meeting",
    headline: "Get your board members raising money",
    headlineAccent: "by your next board meeting",
    topic: "Board fundraising",
    excerpt: "Bring your board into creating the fundraising strategy, agree how each member will participate, and equip them to begin raising money with you.",
    image: "board-fundraising-three-steps.png",
    image_alt: "Board members around a table with the fundraising strategy they create together.",
    intro: [
      "I get asked this question over and over again: how do we get our board members to start raising money for our organization?",
      "You may already have board members who care about the mission and know people who could support it, yet fundraising still comes back to you. At the end of another meeting, you leave with the responsibility of finding the money while everyone else waits to hear how it went.",
      "The approach I use begins with bringing those board members into creating the organization's fundraising strategy. Their ideas and relationships become part of the decisions, and each person helps decide how they will participate. People who plan together execute together."
    ],
    takeaway: "Get your board involved in deciding how the organization will raise money, then give each member what they need to carry out their part.",
    steps: [
      {
        id: "before", label: "Before your next board meeting", title: "Give every board member a way to contribute their thinking",
        paragraphs: [
          "Start by sharing your own ideas about who could fund your organization and why they would give. Explain where you would find them, how you would attract them, what you would ask for and the process you would use to raise money from them.",
          "Each board member answers the same five questions independently through the board fundraising planning form, then says how they would feel comfortable participating. Ask each person to focus on one funding audience they believe is a good fit, so the meeting has specific opportunities to consider.",
          "This gives you a way to hear from the member who has useful connections but rarely speaks in meetings, as well as the member who has an idea you have never considered."
        ]
      },
      {
        id: "during", label: "During your next board meeting", title: "Agree on the fundraising approach and each person's part",
        paragraphs: [
          "Bring everyone's ideas into the meeting and decide together who your primary funding audience will be. Agree how you will find and attract those funders regularly, what you will ask them to support and how you will build the relationship toward giving.",
          "For example, a member may know business owners who care about the young people your organization serves. Once the board agrees on that audience and the fundraising process, that member can identify suitable businesses in their network and offer to make an introduction.",
          "Discuss what each person can take responsibility for and what they need to do it. The responsibilities and execution support come from what your board agrees in this meeting."
        ]
      },
      {
        id: "after", label: "After your next board meeting", title: "Equip each member to begin working with you",
        paragraphs: [
          "Each member receives the agreed strategy and a Board Fundraising Portfolio showing how they will support the organization to raise money. Their personal AI assistant understands that strategy and can help create the emails, talking points or other materials they need for their role.",
          "A member who agreed to make an introduction can prepare the message and begin the conversation with a clear understanding of who the organization wants to reach and what should happen next.",
          "By the end of the meeting, your board members can recognize the ideal funders within their networks and know how to begin approaching them. They have a role they helped shape and the tools to act without bringing every task back to you."
        ]
      }
    ],
    closingTitle: "Begin with your own ideas",
    closing: "Answer the five fundraising questions about your organization. Your answers become the starting point for the strategy you and your board will create together.",
    offerNote: "The five questions are free. After answering, watch the explanation and choose the paid service to bring your board through the planning process and receive the strategy, portfolios and personal assistants.",
    cardLabel: "Get your board participating",
    visualTitle: "A meeting that leads to action",
    visualItems: ["Each member shares their ideas", "Your board agrees on the strategy", "Every member has a role and tools"]
  },
  {
    slug: "three-steps-to-create-your-fundraising-strategy",
    title: "Three steps to create the right fundraising strategy for your organization",
    headline: "Create the right fundraising strategy",
    headlineAccent: "for your organization",
    topic: "Fundraising strategy",
    excerpt: "Decide who your ideal funders are, how to find and attract them, what to ask for and the process to raise money, with your board involved from the beginning.",
    image: "fundraising-strategy-three-steps.png",
    image_alt: "The board identifies a primary funding audience and agrees on how to find, attract and raise money from those funders.",
    intro: [
      "One question I hear from nonprofit founders and executive directors is: what is the best approach to raising money that will work for my organization?",
      "When you need funding, it is easy to move from one fundraising idea to another. Someone suggests an event, another person recommends grants, and you hear about an organization doing well with corporate sponsorships. You can spend months trying different activities while still wondering where your next funding will come from.",
      "The approach to fundraising is the first thing I look at. A useful strategy makes it clear who you will raise money from and why those people would give, then explains how you will reach them and move the relationship toward funding. Your board can help you create that strategy and build the system that puts it to work."
    ],
    takeaway: "Your fundraising strategy should identify your primary funding audience and the exact process your organization will use to raise money from them.",
    steps: [
      {
        id: "before", label: "Step 1", navLabel: "Gather the ideas", title: "Bring your own thinking and your board's ideas together",
        paragraphs: [
          "Before your next board meeting, answer five questions about how you think the organization can raise money. Focus on one audience you believe could fund your work, and explain your thinking in your own words."
        ],
        questions: [
          "Who could fund your organization, and why would they give?",
          "Where can you find them?",
          "How can you attract them and get them interested?",
          "What should you ask them to support, and how much should you ask for?",
          "What process would move them from discovering your organization to funding it?"
        ],
        afterQuestions: "Each board member answers these questions independently and shares how they would feel comfortable participating. You now have several perspectives to consider, including opportunities connected to the people your board already knows."
      },
      {
        id: "during", label: "Step 2", navLabel: "Agree on the approach", title: "Agree on the audience and the process that fit your organization",
        paragraphs: [
          "During the meeting, look at the proposed audiences alongside the funders who already support your organization. Consider their reasons for giving, your ability to reach them and what you can offer them an opportunity to support.",
          "Decide who your primary funding audience will be and agree how you will find and attract them on a daily basis. Work through what you will ask for, how much you will ask and the steps that should lead to a funding decision.",
          "If your audience is former participants who now have the means to give, for example, your process might begin with reconnecting and sharing what the program is achieving. From there, you can invite a conversation about supporting the next group of participants and make a specific ask.",
          "By the end of the discussion, the board should be able to explain the approach and understand why it fits your organization."
        ]
      },
      {
        id: "after", label: "Step 3", navLabel: "Equip your board", title: "Give your board the strategy and the tools to put it to work",
        paragraphs: [
          "Agree in the meeting how each board member will contribute and what support they need. Those decisions become part of the strategy's execution section, and each member receives a Board Fundraising Portfolio showing their part.",
          "Their personal AI assistant understands the agreed strategy and helps create the content or materials they need to carry out their responsibilities. Someone helping to attract potential funders can prepare relevant content, while a member making an introduction can create a message suited to that relationship.",
          "As your organization begins to carry out the process consistently, you and your board can build the fundraising system that drives the strategy at scale. The strategy gives that work a clear direction, and your board has already helped decide how to support it."
        ]
      }
    ],
    closingTitle: "Start creating your organization's strategy",
    closing: "Share your thinking through the five fundraising questions. That is the first step toward creating a strategy your board understands and can work with you to execute.",
    offerNote: "The five questions are free. After answering, watch the explanation and choose the paid service to bring your board through the planning process and receive the strategy, portfolios and personal assistants.",
    cardLabel: "Find the right fundraising approach",
    visualTitle: "Give your fundraising a direction",
    visualItems: ["Identify your ideal funding audience", "Agree on the process to raise money", "Equip your board to carry it out"]
  }
];

const articleBySlug = (slug) => articles.find(article => article.slug === slug);
const articleForPath = (pathname) => articleBySlug(pathname.replace(/\/+$/, "").replace(/^\/blog\//, ""));
const articlePath = (article) => `/blog/${article.slug}`;
const articleWordCount = (article) => [article.title, ...article.intro, ...article.steps.flatMap(step => [step.title, ...step.paragraphs, ...(step.questions || []), step.afterQuestions || ""]), article.closingTitle, article.closing, article.offerNote].join(" ").split(/\s+/).length;
const articlePost = (article) => ({
  ...article, category: article.topic, category_key: "fundraising_activation",
  published_at: "2026-10-06T10:53:37Z", author_url: "https://nonprofitboardbuilder.com/",
  image_url: `https://nonprofitboardbuilder.com/social/${article.image}`,
  body: [...article.intro, ...article.steps.flatMap(step => [`## ${step.label}: ${step.title}`, ...step.paragraphs, ...(step.questions || []), step.afterQuestions || ""])].filter(Boolean).join("\n\n"),
  cta_url: START_PATH, cta_label: article.closingTitle, cta_button: CTA
});

module.exports = { articles, START_PATH, CTA, articleBySlug, articleForPath, articlePath, articlePost, articleWordCount };

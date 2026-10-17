export const FIVE_QUESTIONS = [
  {
    key: "audience",
    title: "From your point of view, who is one audience that could help your organization reach this fundraising goal, and why do you think they would give to your organization?",
    hint: "Choose one particular type of person, business or grantmaker. Tell us what connects them to your mission or the people you serve.",
  },
  {
    key: "where",
    title: "Where do you think we can actually find the kind of people you just identified? Where do they spend their time, work, gather, network, belong or pay attention?",
  },
  {
    key: "attraction",
    title: "How do you think we can get the attention of these people and make them interested in our organization and what we do?",
  },
  {
    key: "funding_ask",
    title: "If we eventually get in front of these people, what should we actually ask them for? And how much should we ask for?",
  },
  {
    key: "process",
    title: "We probably cannot meet these people for the first time and immediately ask them for money. So from the first time they hear about us, what do you think the step-by-step process should be for building that relationship and eventually getting them to give?",
  },
];

export const fiveQuestionText = (index, audience = "") => {
  if (index !== 1 || !audience) return FIVE_QUESTIONS[index].title;
  const noun = /foundation|grantmaker|grantor|funder|agency/i.test(audience) ? "funders" :
    /business|compan|corporat|employer|sponsor/i.test(audience) ? "organizations" : "people";
  return FIVE_QUESTIONS[index].title.replace("people", noun);
};

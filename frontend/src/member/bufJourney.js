// Complete Board Fix (Board Ultimate Fix) journey map.
// When a member holds the board_fix_system entitlement, this sequence OVERRIDES
// the standalone course next/previous destinations — the customer never leaves
// the Complete Board Fix journey.

const ROUTES = {
  reactivation: (m) => `/app/reactivation/self-guided/module/${m}`,
  recruitment: (m) => `/app/recruitment/self-guided/module/${m}`,
  activation: (m) => `/app/activation/self-guided/module/${m}`,
};

export const BUF_SEQUENCE = [
  { pathway: "reactivation", module: 3 },
  { pathway: "reactivation", module: 4 },
  { pathway: "reactivation", module: 5 },
  { pathway: "recruitment", module: 2 },
  { pathway: "recruitment", module: 3 },
  { pathway: "recruitment", module: 4 },
  { pathway: "recruitment", module: 5 },
  { pathway: "recruitment", module: 6 },
  { pathway: "activation", module: 2 },
  { pathway: "activation", module: 3 },
  { pathway: "activation", module: 4 },
  { pathway: "activation", module: 5 },
];

export const bufStep = (member, pathway, moduleNumber) => {
  if (!member?.entitlements?.includes("board_fix_system")) return null;
  const index = BUF_SEQUENCE.findIndex((s) => s.pathway === pathway && s.module === moduleNumber);
  if (index === -1) return null;
  const route = (s) => ROUTES[s.pathway](s.module);
  return {
    next: index + 1 < BUF_SEQUENCE.length ? route(BUF_SEQUENCE[index + 1]) : "/board-fix-roadmap",
    prev: index > 0 ? route(BUF_SEQUENCE[index - 1]) : "/board-fix-orientation",
  };
};

export const TIERS = {
  A: { label: "Strong fit", className: "tier-a" },
  B: { label: "Good fit", className: "tier-b" },
  C: { label: "Weak fit", className: "tier-c" },
  D: { label: "Poor fit", className: "tier-d" },
};

// Components are grouped by the question they answer, and colored by group.
export const COMPONENT_GROUPS = {
  maturity: "business",
  size: "business",
  industry: "business",
  recurring: "opportunity",
  succession: "opportunity",
  upside: "opportunity",
  reachability: "access",
};

export const GROUP_LABELS = {
  business: "Is it a solid business?",
  opportunity: "Is there an opportunity?",
  access: "Can you reach the owner?",
};

export const STAGES = [
  { value: "new", label: "New" },
  { value: "shortlist", label: "Shortlist" },
  { value: "contacted", label: "Contacted" },
  { value: "passed", label: "Passed" },
];

export const EMAIL_STATUS = {
  valid: { label: "Direct email", tone: "good" },
  personal_domain: { label: "Personal email", tone: "good" },
  role: { label: "General inbox", tone: "watch" },
  unverified: { label: "Unverified", tone: "watch" },
  invalid: { label: "Invalid email", tone: "risk" },
};

export const SIGNAL_TAGS = {
  succession: "Owner transition",
  family_owned: "Family owned",
  recurring: "Recurring revenue",
  hiring: "Hiring",
};

export const PAGE_NAMES = { home: "Home page", about: "About page", services: "Services page", contact: "Contact page", careers: "Careers page" };

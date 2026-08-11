// CANONICAL TESTIMONIALS — founder-supplied source material. LOCKED.
// Never paraphrase, shorten, correct grammar/typos, add results, or let AI rewrite.
// Every testimonial section in the application must import from this file.
export const testimonials = [
  {
    name: "Martina Jones",
    organization: "Bless It Solutions, SC",
    quote: "Working with Rooney has inspired myself and my board members to continue going forward with the mission. Each member understands the overall mission and how they play a critical role in going forward. For much of the time as the Founder and Executive Director I came to a point where I felt stuck. Rooney was able to strategically help Bless It Solutions map out a plan where each board members are able to take charge in their area of expertise. He was also able to get the board members engaged and ready to help make an impact in our community. We are all so grateful for the opportunity for the board retreat which was much needed.",
  },
  {
    name: "Tony Barnes",
    organization: "Founder, Another Blessed Ministry",
    quote: "I was running on fumes, trying to fundraise, manage a full-time job, and build a board all by myself. Rooney's fundraising system changed everything. Not only did we successfully recruit our new board, but we now have volunteers focused on specific areas, from social media to direct fundraising. I now spend less time weekly managing the structure, and the mission finally has momentum. I stopped drowning and started leading. This is the game-changer I always wanted.",
  },
  {
    name: "Laura Anthony",
    organization: "Zero Waste San Diego",
    quote: "Rooney really knows his stuff. He has helped my board rethink how we fundraise and even changed how we value ourselves and our services. He provides quick and well-thought-out fundraising plans that are easy to follow, giving us the tools and confidence to implement. Highly recommend!",
  },
  {
    name: "Linda Floyd",
    organization: "Battle Buddies of Central Oregon",
    quote: "We were unsure as to raising money in these modern times for our nonprofit organization focused on preventing veteran suicide through canine companionship. Rooney gave us valuable fundraising insight and created a simple and organized fundraising plan I and my team can follow to raise money for our mission. Many Blessings Rooney, we appreciate you.",
  },
  {
    name: "Devona Boone",
    organization: "Natalie’s Place Transitional Housing, VA",
    quote: "Mr Rooney did an outstanding job! The Board Leadership training gave me principles and resources to apply to recruiting board members and how to properly keep them engaged. I feel like I have the tools I need to be a great Board Leader and lead my team to executing plans we set out to reach. Thank you again for giving me structure for my Board of Directors.",
  },
  {
    name: "Donna Kargel",
    organization: "Community Thrive, FL",
    quote: "Rooney is our consultant at Community Thrive a nonprofit to help youth become independent. I waisted 6 months not knowing what I don't know before I hired him as a consultant. We accomplished in 4 months a board, a volunteer program currently staffed with & volunteers, a strategic plan for funding and too much to share. If you are on the fence, reach out to me. I would be happy to tell you why you can't afford not to hire him.",
  },
  {
    name: "Donna Kargel",
    organization: "Community Thrive, Florida",
    quote: "Rooney is our consultant at Community Thrive a nonprofit to help youth become independent. He has helped our board to understand their roles and hold board meetings. He has helped us to see other possibilities for fundraising and events. He is easy to listen to and open to suggestions. He has great ideas that we are able to implement. Thank you for all your help.",
  },
  {
    name: "Pastor Cyrena Denniston",
    organization: "Founder, Blackfire Ministries",
    quote: "Because of your, uh, input and your investment in my life as the founder and visionary, Blackfire Ministries, we now have a working board. We now have a fundraising fellowship of individuals that are passionate about what we do. It has been an incredible journey, and I'm very thankful for you.",
  },
];

export const initialsFor = (name) =>
  name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("");

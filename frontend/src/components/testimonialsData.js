export const testimonials = [
  {
    name: "Martina Jones",
    organization: "Bless It Solutions",
    quote: "Working with Rooney Akpesiri, the Nonprofit Board Builder, has inspired myself and my board members to continue going forward with the mission. Each member understands the overall mission and how they play a critical role in going forward. Rooney Akpesiri, the Nonprofit Board Builder, was able to strategically help Bless It Solutions map out a plan where each board member is able to take charge in their area of expertise. He got the board engaged and ready to help make an impact in our community.",
    result: "Board members became engaged and took responsibility in their areas of expertise.",
    featured: true,
  },
  {
    name: "Pastor Cyrena Denniston",
    organization: "Founder, Black Fire Ministries",
    quote: "Before Rooney Akpesiri, the Nonprofit Board Builder, and I started working together, Black Fire Ministries was definitely growing and building, but we knew we couldn’t stay where we were. We needed the next level. We needed more sustainability and a stronger foundation for the future. Black Fire Ministries now has a working board and a fundraising fellowship of people who are passionate about our mission.",
    result: "Built a working board and a fundraising fellowship.",
    featured: true,
  },
  {
    name: "Tony Barnes",
    organization: "Founder, Another Blessed Ministry",
    quote: "I was running on fumes, trying to fundraise, manage a full-time job, and build a board all by myself. Rooney Akpesiri’s fundraising system changed everything. Not only did we successfully recruit our new board, but we now have volunteers focused on specific areas, from social media to direct fundraising. I now spend less time weekly managing the structure, and the mission finally has momentum. I stopped drowning and started leading. This is the game-changer I always wanted.",
    result: "Recruited a new board and built a volunteer fundraising structure.",
    featured: true,
  },
  {
    name: "Donna Kargel",
    organization: "Community Thrive",
    quote: "We accomplished in 4 months a board, a volunteer program staffed with 8 volunteers, a strategic plan for funding, and too much to share. If you are on the fence, reach out to me. You can’t afford not to hire him.",
    result: "Built a board, recruited eight volunteers and created a strategic funding plan in four months.",
  },
  {
    name: "Laura Anthony",
    organization: "Zero Waste San Diego",
    quote: "Rooney Akpesiri, the Nonprofit Board Builder, really knows his stuff. He has helped my board rethink how we fundraise and even changed how we value ourselves and our services. He provides quick and well-thought-out fundraising plans that are easy to follow, giving us the tools and confidence to implement. Highly recommend!",
    result: "Helped the board rethink fundraising and confidently implement a new plan.",
  },
  {
    name: "Linda Floyd",
    organization: "Battle Buddies of Central Oregon",
    quote: "We were unsure as to raising money in these modern times for our nonprofit organization focused on preventing veteran suicide through canine companionship. Rooney Akpesiri, the Nonprofit Board Builder, gave us valuable fundraising insight and created a simple and organized fundraising plan I and my team can follow to raise money for our mission. Many Blessings Rooney, we appreciate you.",
    result: "Created a simple and organized fundraising plan the team could follow.",
  },
  {
    name: "Devona Boone",
    organization: "Natalie’s Place",
    quote: "Rooney Akpesiri, the Nonprofit Board Builder, has the tools to help us have a stronger board that will be engaged. I’m excited to start our journey with him.",
    result: "A clear path toward building a stronger and more engaged board.",
  },
];

export const initialsFor = (name) => name.replace("Pastor ", "").split(" ").map((part) => part[0]).join("").slice(0, 2);

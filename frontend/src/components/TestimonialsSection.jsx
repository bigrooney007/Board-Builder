import { useEffect, useState } from "react";
import { ImagePlus, Quote } from "lucide-react";

const testimonials = [
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

const initialsFor = (name) => name.replace("Pastor ", "").split(" ").map((part) => part[0]).join("").slice(0, 2);

const TestimonialCard = ({ testimonial, index }) => {
  const [photo, setPhoto] = useState("");
  const [logo, setLogo] = useState("");
  useEffect(() => () => {
    if (photo) URL.revokeObjectURL(photo);
    if (logo) URL.revokeObjectURL(logo);
  }, [photo, logo]);
  const replacePhoto = (event) => {
    const file = event.target.files?.[0];
    if (file) setPhoto(URL.createObjectURL(file));
  };
  const replaceLogo = (event) => {
    const file = event.target.files?.[0];
    if (file) setLogo(URL.createObjectURL(file));
  };

  return (
    <article className={`testimonial-card ${testimonial.featured ? "featured" : "supporting"}`} data-testid={`testimonial-card-${index + 1}`}>
      <div className="testimonial-card-top">
        <div className="client-avatar" data-testid={`testimonial-avatar-${index + 1}`}>
          {photo ? <img src={photo} alt={`${testimonial.name} approved portrait`} data-testid={`testimonial-photo-${index + 1}`} /> : <span data-testid={`testimonial-initials-${index + 1}`}>{initialsFor(testimonial.name)}</span>}
        </div>
        <div className="client-identity"><strong data-testid={`testimonial-name-${index + 1}`}>{testimonial.name}</strong><span data-testid={`testimonial-organization-${index + 1}`}>{testimonial.organization}</span></div>
        <div className="organization-logo" data-testid={`testimonial-organization-logo-${index + 1}`}>{logo ? <img src={logo} alt={`${testimonial.organization} approved logo`} /> : <span>{testimonial.organization.charAt(0)}</span>}</div>
        <Quote className="quote-mark" size={27} aria-hidden="true" />
      </div>
      <blockquote data-testid={`testimonial-quote-${index + 1}`}>“{testimonial.quote}”</blockquote>
      <p className="testimonial-result" data-testid={`testimonial-result-${index + 1}`}><span>Result</span>{testimonial.result}</p>
      <div className="testimonial-media-controls">
        <label className="photo-replace-control" data-testid={`testimonial-photo-replace-control-${index + 1}`}><ImagePlus size={14} /> {photo ? "Replace approved photo" : "Add approved photo"}<input type="file" accept="image/*" onChange={replacePhoto} data-testid={`testimonial-photo-upload-${index + 1}`} /></label>
        <label className="photo-replace-control" data-testid={`testimonial-logo-replace-control-${index + 1}`}><ImagePlus size={14} /> {logo ? "Replace organization logo" : "Add organization logo"}<input type="file" accept="image/*" onChange={replaceLogo} data-testid={`testimonial-logo-upload-${index + 1}`} /></label>
      </div>
    </article>
  );
};

export const TestimonialsSection = () => {
  const featured = testimonials.filter((item) => item.featured);
  const supporting = testimonials.filter((item) => !item.featured);
  return (
    <section id="success-stories" className="section testimonials-section" data-testid="testimonials-section">
      <div className="testimonials-heading">
        <p className="eyebrow" data-testid="testimonials-eyebrow">Success stories</p>
        <h2 data-testid="testimonials-heading">Nonprofit Leaders We Have Helped Build Stronger Boards and Fundraising Systems</h2>
        <p data-testid="testimonials-supporting-text">Founders and executive directors have worked with the Nonprofit Board Builder to recruit board members, activate their boards, build fundraising systems, recruit volunteers and create a clear structure for moving their missions forward.</p>
      </div>
      <div className="featured-testimonials" data-testid="featured-testimonials-grid">
        {featured.map((testimonial, index) => <TestimonialCard testimonial={testimonial} index={index} key={testimonial.name} />)}
      </div>
      <div className="supporting-testimonials" data-testid="supporting-testimonials-grid">
        {supporting.map((testimonial, index) => <TestimonialCard testimonial={testimonial} index={index + featured.length} key={testimonial.name} />)}
      </div>
    </section>
  );
};
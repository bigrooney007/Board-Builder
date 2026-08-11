import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Quote } from "lucide-react";
import { initialsFor, testimonials } from "./testimonialsData";

const TestimonialCard = ({ testimonial, index }) => {
  return (
    <article className={`testimonial-card ${testimonial.featured ? "featured" : "supporting"}`} data-testid={`testimonial-card-${index + 1}`}>
      <div className="testimonial-card-top">
        <div className="client-avatar" data-testid={`testimonial-avatar-${index + 1}`}>
          <span data-testid={`testimonial-initials-${index + 1}`}>{initialsFor(testimonial.name)}</span>
        </div>
        <div className="client-identity"><strong data-testid={`testimonial-name-${index + 1}`}>{testimonial.name}</strong><span data-testid={`testimonial-organization-${index + 1}`}>{testimonial.organization}</span></div>
        <Quote className="quote-mark" size={27} aria-hidden="true" />
      </div>
      <blockquote data-testid={`testimonial-quote-${index + 1}`}>“{testimonial.quote}”</blockquote>
      {testimonial.result && <p className="testimonial-result" data-testid={`testimonial-result-${index + 1}`}><span>Result</span>{testimonial.result}</p>}
    </article>
  );
};

export const TestimonialsSection = () => {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused) return undefined;
    const timer = window.setInterval(() => setActive((current) => (current + 1) % testimonials.length), 7000);
    return () => window.clearInterval(timer);
  }, [paused]);
  return (
    <section id="success-stories" className="section testimonials-section" data-testid="testimonials-section">
      <div className="testimonials-heading">
        <p className="eyebrow" data-testid="testimonials-eyebrow">Success stories</p>
        <h2 data-testid="testimonials-heading">Nonprofit Leaders We Have Helped Build Stronger Boards and Fundraising Systems</h2>
        <p data-testid="testimonials-supporting-text">Founders and executive directors have worked with the Nonprofit Board Builder to recruit board members, activate their boards, build fundraising systems, recruit volunteers and create a clear structure for moving their missions forward.</p>
      </div>
      <div className="testimonial-slideshow" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} data-testid="testimonial-slideshow">
        <div className="testimonial-track" style={{ transform: `translateX(-${active * 100}%)` }}>{testimonials.map((testimonial, index) => <div className="testimonial-slide" key={`${testimonial.name}-${index}`} aria-hidden={active !== index}><TestimonialCard testimonial={testimonial} index={index} /></div>)}</div>
      </div>
      <div className="testimonial-controls"><button onClick={() => setActive((active - 1 + testimonials.length) % testimonials.length)} aria-label="Previous testimonial" data-testid="testimonial-previous-button"><ChevronLeft /></button><div className="testimonial-dots">{testimonials.map((testimonial, index) => <button className={active === index ? "active" : ""} onClick={() => setActive(index)} aria-label={`Show testimonial from ${testimonial.name}`} key={`${testimonial.name}-${index}`} data-testid={`testimonial-dot-${index + 1}`} />)}</div><span data-testid="testimonial-slide-count">{active + 1} / {testimonials.length}</span><button onClick={() => setActive((active + 1) % testimonials.length)} aria-label="Next testimonial" data-testid="testimonial-next-button"><ChevronRight /></button></div>
    </section>
  );
};
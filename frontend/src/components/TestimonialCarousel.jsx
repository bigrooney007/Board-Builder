import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Quote } from "lucide-react";
import { initialsFor, testimonials } from "./testimonialsData";

export const TestimonialCarousel = ({ heading, idPrefix = "carousel" }) => {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const touchStart = useRef(null);
  const count = testimonials.length;

  useEffect(() => {
    if (paused) return undefined;
    const timer = window.setInterval(() => setActive((current) => (current + 1) % count), 8000);
    return () => window.clearInterval(timer);
  }, [paused, count]);

  const go = (next) => setActive(((next % count) + count) % count);
  const onTouchStart = (event) => { touchStart.current = event.touches[0].clientX; setPaused(true); };
  const onTouchEnd = (event) => {
    if (touchStart.current === null) return;
    const delta = event.changedTouches[0].clientX - touchStart.current;
    if (Math.abs(delta) > 45) go(active + (delta < 0 ? 1 : -1));
    touchStart.current = null;
    setPaused(false);
  };

  return (
    <section className="section offer-testimonials" data-testid={`${idPrefix}-testimonial-section`}>
      <h2 data-testid={`${idPrefix}-testimonial-heading`}>{heading}</h2>
      <div
        className="offer-carousel"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        data-testid={`${idPrefix}-testimonial-carousel`}
      >
        <div className="offer-carousel-track" style={{ transform: `translateX(-${active * 100}%)` }}>
          {testimonials.map((testimonial, index) => (
            <div className="offer-carousel-slide" key={testimonial.name} aria-hidden={active !== index}>
              <article className="offer-testimonial-card" data-testid={`${idPrefix}-testimonial-card-${index + 1}`}>
                <div className="testimonial-card-top">
                  <div className="client-avatar"><span>{initialsFor(testimonial.name)}</span></div>
                  <div className="client-identity">
                    <strong data-testid={`${idPrefix}-testimonial-name-${index + 1}`}>{testimonial.name}</strong>
                    <span>{testimonial.organization}</span>
                  </div>
                  <Quote className="quote-mark" size={25} aria-hidden="true" />
                </div>
                <blockquote>“{testimonial.quote}”</blockquote>
                <p className="testimonial-result"><span>Result</span>{testimonial.result}</p>
              </article>
            </div>
          ))}
        </div>
      </div>
      <div className="testimonial-controls">
        <button type="button" onClick={() => go(active - 1)} aria-label="Previous testimonial" data-testid={`${idPrefix}-testimonial-previous`}><ChevronLeft /></button>
        <div className="testimonial-dots">
          {testimonials.map((testimonial, index) => (
            <button type="button" className={active === index ? "active" : ""} onClick={() => go(index)} aria-label={`Show testimonial from ${testimonial.name}`} key={testimonial.name} data-testid={`${idPrefix}-testimonial-dot-${index + 1}`} />
          ))}
        </div>
        <span data-testid={`${idPrefix}-testimonial-count`}>{active + 1} / {count}</span>
        <button type="button" onClick={() => go(active + 1)} aria-label="Next testimonial" data-testid={`${idPrefix}-testimonial-next`}><ChevronRight /></button>
      </div>
    </section>
  );
};

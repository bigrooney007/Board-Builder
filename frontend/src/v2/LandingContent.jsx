import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PRODUCTS, SELF_SERVICE_PRICE } from "./content";

export function defaultLandingContent(product) {
  const source = PRODUCTS[product];
  return {
    eyebrow: source.eyebrow, headline: source.headline, intro: source.intro,
    hero_note: "Learn the process and share your starting information before you decide to purchase.",
    education_eyebrow: "HOW TO CARRY OUT THE PROCESS", education_heading: "What you and your organization will do",
    teaching: source.teaching.map((step) => [...step]),
    service_heading: "Get the tools and carry out the work yourself.", outcome: source.outcome,
    service_body: `You can follow this process without necessarily spending thousands of dollars on consultants. The self-service service costs $${SELF_SERVICE_PRICE} for this product. If you want us to work with you or provide more direct help, book a conversation and we will discuss a separate quotation.`,
    closing_heading: "Start with what you know about your organization.",
    closing_body: "The free questions help us understand your situation. You will then see exactly what happens next and what your purchase includes.",
  };
}

function Paragraphs({ text }) {
  return String(text || "").split(/\n\s*\n/).map((paragraph, index) => <p className="v2-landing-paragraph" key={index}>{paragraph}</p>);
}

export default function LandingContent({ product, content, preview = false }) {
  const source = PRODUCTS[product];
  const start = `/v2/${product}/start`;
  const cta = <Link className="v2-button" to={start} {...(preview ? { target: "_blank", rel: "noopener noreferrer" } : {})}>Start for Free<ArrowRight size={18} aria-hidden="true" /></Link>;
  return <>
    <section className="v2-hero"><div className="v2-hero-copy"><p className="v2-eyebrow">{content.eyebrow}</p><h1>{content.headline}</h1><Paragraphs text={content.intro} />{cta}<span className="v2-hero-note">{content.hero_note}</span></div><img className="v2-product-image" src={source.image} alt={`${source.name} from Nonprofit Board Builder`} /></section>
    <section className="v2-education" aria-labelledby={preview ? "v2-preview-process" : "v2-process"}><p className="v2-eyebrow">{content.education_eyebrow}</p><h2 id={preview ? "v2-preview-process" : "v2-process"}>{content.education_heading}</h2><ol className="v2-steps">{content.teaching.map(([heading, paragraph], index) => <li key={index}><span className="v2-step-number" aria-hidden="true">{index + 1}</span><div><h3>{heading}</h3><Paragraphs text={paragraph} /></div></li>)}</ol>{cta}</section>
    <section className="v2-service-explanation"><h2>{content.service_heading}</h2><Paragraphs text={content.outcome} /><Paragraphs text={content.service_body} /></section>
    <TestimonialCarousel heading="What Nonprofit Leaders We Have Worked With Are Saying" idPrefix={`${preview ? "v2-editor" : "v2"}-${product}`} />
    <section className="v2-closing"><h2>{content.closing_heading}</h2><Paragraphs text={content.closing_body} />{cta}</section>
  </>;
}

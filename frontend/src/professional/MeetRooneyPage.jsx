import {Link} from 'react-router-dom';
import {TestimonialCarousel} from '@/components/TestimonialCarousel';
import {testimonials} from '@/content/testimonials';
import {useLandingPageMeta} from '@/seo';
import {useProfessionalContent,logoUrl} from './content';
import RichContent from './RichContent';
import '@/pages/MainHomePage.css';
import './professional.css';

export default function MeetRooneyPage(){
 useLandingPageMeta('/meet-rooney');
 const c=useProfessionalContent('personal');
 const selected=c.testimonialIds.map(i=>testimonials[i]).filter(Boolean);
 return <div className="nBB-home professional-page" data-testid="meet-rooney-page">
  <header className="nBB-home-nav professional-nav"><Link className="nBB-home-brand" to="/"><img src={logoUrl} alt="Nonprofit Board Builder" style={{width:130,height:68,objectFit:"contain"}}/></Link><nav><Link to="/">{c.homeNav}</Link><Link to="/blog">{c.blogNav}</Link><Link to="/join-a-board">{c.networkNav}</Link></nav></header>
  <main>
   <section className="professional-intro professional-width"><img className="professional-portrait" src={c.portrait} alt={c.portraitAlt} width="420" height="500" fetchPriority="high"/><div><h1>{c.headline}</h1><RichContent text={c.introduction}/><RichContent text={c.experience}/><a className="nBB-home-primary" href="/consultation">{c.consultationCta} · $197</a></div></section>
   <section className="professional-section professional-tint"><div className="professional-copy"><h2>{c.philosophyHeading}</h2><RichContent text={c.philosophy}/></div></section>
   <section className="professional-section"><div className="professional-copy"><h2>{c.servicesHeading}</h2><RichContent text={c.services}/></div></section>
   <section className="professional-section professional-navy" id="consultation"><div className="professional-copy"><h2>{c.consultationHeading}</h2><RichContent text={c.consultationDescription}/><p className="professional-price">{c.consultationLabel}: $197</p><a className="nBB-home-primary" href="/consultation">{c.consultationCta} · $197</a></div></section>
   <section className="professional-section professional-width"><h2>{c.productsHeading}</h2><div className="nBB-home-grid"><article className="professional-product"><h3>{c.fundraisingHeading}</h3><RichContent text={c.fundraisingDescription}/><a className="nBB-home-primary" href={c.fundraisingUrl} target="_blank" rel="noreferrer">{c.fundraisingCta}</a></article><article className="professional-product"><h3>{c.gameHeading}</h3><RichContent text={c.gameDescription}/><a className="nBB-home-primary" href={c.gameUrl}>{c.gameCta}</a></article></div></section>
   {selected.length>0&&<section className="nBB-home-proof"><TestimonialCarousel heading={c.testimonialsHeading} idPrefix="rooney" items={selected}/></section>}
  </main><footer className="nBB-home-footer"><Link to="/">Nonprofit Board Builder</Link><Link to="/privacy-policy">Privacy</Link><Link to="/terms">Terms</Link></footer>
 </div>;
}

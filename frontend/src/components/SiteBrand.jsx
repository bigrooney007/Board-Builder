import {Link} from 'react-router-dom';
import {SITE_LOGO_URL} from '@/content/branding';

export function SiteBrand(){return <Link to="/" className="site-brand" aria-label="Nonprofit Board Builder home"><img src={SITE_LOGO_URL} alt="Nonprofit Board Builder" width="150" height="110"/></Link>}

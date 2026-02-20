import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ValueProposition from './components/ValueProposition';
import BriefingExplainer from './components/BriefingExplainer';
import HowItWorks from './components/HowItWorks';
import Pricing from './components/Pricing';
import SocialProof from './components/SocialProof';
import CTASection from './components/CTASection';
import EditionsPreviews from './components/EditionsPreviews';
import ForCompanies from './components/ForCompanies';
import FAQ from './components/FAQ';
import Manifesto from './components/Manifesto';
import Footer from './components/Footer';

function App() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />
      <Hero />
      <ValueProposition />
      <BriefingExplainer />
      <HowItWorks />
      <Pricing />
      <SocialProof />
      <CTASection />
      <EditionsPreviews />
      <ForCompanies />
      <FAQ />
      <Manifesto />
      <Footer />
    </div>
  );
}

export default App;

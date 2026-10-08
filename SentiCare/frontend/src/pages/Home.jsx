import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Illustration1 from "../assets/Illustration_1.svg";
import Illustration2 from "../assets/Illustration_2.svg";
import Illustration3 from "../assets/Illustration_3.svg";
import Illustration4 from "../assets/mindfullness.svg";
import Illustration5 from "../assets/oneonone.svg";
import Illustration6 from "../assets/illustration_6.svg";
import CommunityIllustration from "../assets/Illustration_11.svg";

import LoginModal from "../components/LoginModal";

const LandingPage = () => {
  const [showLogin, setShowLogin] = useState(false);
  const navigate = useNavigate();

  const handleGetStarted = () => {
    setShowLogin(true);
  };

  // Smooth scroll to section
  const scrollToSection = (id) => {
    const section = document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center overflow-y-auto scroll-smooth">
      {/* Navigation - Fixed */}
      <nav className="fixed top-0 left-0 right-0 w-full flex items-center justify-between px-16 py-6 bg-white z-40 shadow-sm">
        <div className="flex items-center space-x-10">
          <button
            onClick={() => navigate("/dashboard")}
            className="text-gray-700 hover:text-gray-900 font-medium cursor-pointer"
          >
            Home
          </button>
          <button
            onClick={() => scrollToSection("about")}
            className="text-gray-700 hover:text-gray-900 font-medium cursor-pointer"
          >
            About
          </button>
        </div>

        <Link
          to="/"
          className="absolute left-1/2 transform -translate-x-1/2 text-2xl font-bold text-teal-900"
        >
          Maitri
        </Link>

        <div className="flex items-center space-x-10">
          <button
            onClick={() => scrollToSection("services")}
            className="text-gray-700 hover:text-gray-900 font-medium cursor-pointer"
          >
            Services
          </button>
          <button
            onClick={() => scrollToSection("resources")}
            className="text-gray-700 hover:text-gray-900 font-medium cursor-pointer"
          >
            Resources
          </button>
        </div>
      </nav>

      <div className="pt-20 w-full"></div>

      {/* Hero Section */}
      <section
        id="hero"
        className="relative w-[90%] max-w-[1400px] flex justify-center items-center bg-[#F9E6D0] overflow-hidden py-24 rounded-[40px] mx-auto"
      >
        <img
          src={Illustration2}
          alt="Left Illustration"
          className="absolute left-0 bottom-0 h-[90%] w-auto object-contain hidden md:block"
        />
        <img
          src={Illustration1}
          alt="Right Illustration"
          className="absolute right-0 bottom-0 h-[90%] w-auto object-contain hidden md:block"
        />

        <div className="relative text-center px-6 max-w-xl z-10">
          <h1 className="text-5xl md:text-6xl font-extrabold text-[#1A3A37] leading-tight">
            Support for Your <br /> Mental Well-being
          </h1>
          <p className="mt-4 text-gray-800 text-lg leading-relaxed">
            Connect with licensed therapists, counselors, <br />
            and wellness coaches to support your journey.
          </p>
          <button
            onClick={handleGetStarted}
            className="mt-8 px-8 py-3 bg-[#1A3A37] hover:bg-[#154F4A] text-white font-medium rounded-full text-sm transition-all duration-200 shadow-md"
          >
            Get Started
          </button>
        </div>
      </section>

      {/* About Section */}
      <section
        id="about"
        className="w-[90%] max-w-[1100px] flex flex-col md:flex-row items-center justify-between py-24 gap-12"
      >
        <div className="flex-1 text-left">
          <p className="text-sm tracking-wider text-gray-500 font-semibold mb-3">
            HOW IT WORKS
          </p>
          <h2 className="text-4xl md:text-5xl font-extrabold text-[#1A3A37] leading-tight mb-6">
            We Help You <br /> Prioritize Your <br /> Mental Health
          </h2>
          <p className="text-gray-700 text-lg mb-8">
            Browse therapists, book a session, and start your healing journey
            with trusted professionals.
          </p>
          <button className="px-8 py-3 bg-[#1A3A37] hover:bg-[#154F4A] text-white font-medium rounded-full text-sm transition-all duration-200 shadow-md">
            Find A Therapist
          </button>
        </div>

        <div className="flex-1 flex justify-center">
          <div className="bg-[#00373E] p-10 rounded-[40px]">
            <img
              src={Illustration3}
              alt="Mental Health Illustration"
              className="w-[400px] h-auto object-contain"
            />
          </div>
        </div>
      </section>

      {/* Services Section */}
      <section
        id="services"
        className="w-[90%] max-w-[1200px] mx-auto py-24 text-center"
      >
        <p className="text-sm tracking-wider text-gray-500 font-semibold mb-3">
          SERVICES
        </p>
        <h2 className="text-4xl md:text-5xl font-extrabold text-[#1A3A37] mb-4">
          Your Path to <br className="hidden md:block" /> Well-being
        </h2>
        <p className="text-gray-600 text-lg max-w-2xl mx-auto mb-16">
          Discover expert guidance for a healthier mind and balanced life.
        </p>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Mindfulness Image Card */}
          <div className="relative rounded-3xl overflow-hidden shadow-sm">
            <img
              src={Illustration4}
              alt="Mindfulness Illustration"
              className="w-full h-full object-cover"
            />
          </div>

          {/* Therapy Image Card */}
          <div className="relative rounded-3xl overflow-hidden shadow-sm">
            <img
              src={Illustration5}
              alt="Therapy Illustration"
              className="w-full h-full object-cover"
            />
          </div>
        </div>

        {/* Wellness Coaching */}
        <div className="mt-8 bg-white border border-gray-200 rounded-3xl p-10 text-left flex flex-col md:flex-row items-center justify-between shadow-sm relative overflow-hidden">
          <div className="flex-1 mb-6 md:mb-0">
            <h3 className="text-2xl font-bold text-[#1A3A37] mb-3">
              Wellness Coaching
            </h3>
            <p className="text-gray-700 mb-6">
              Personalized guidance to help you build healthier habits, manage
              stress, and achieve balance in all areas of your life.
            </p>
            <p className="text-gray-700 mb-6">
              Our wellness coaches support you in creating sustainable routines
              for mental, emotional, and physical well-being.
            </p>
            <button className="px-6 py-2 border border-[#1A3A37] text-[#1A3A37] font-medium rounded-full text-sm hover:bg-[#1A3A37] hover:text-white transition-all duration-200">
              Learn More
            </button>
          </div>

          <div className="flex-1 flex justify-end">
            <img
              src={Illustration6}
              alt="Wellness Coaching Illustration"
              className="w-[400px] h-auto"
            />
          </div>
        </div>
      </section>

      {/* Community Section */}
      <section
        id="community"
        className="w-[90%] max-w-[1200px] mx-auto bg-white rounded-3xl p-10 flex flex-col md:flex-row items-center justify-between shadow-sm my-16"
      >
        <div className="flex-1 text-left">
          <p className="text-sm tracking-wider text-gray-500 font-semibold mb-3">
            COMMUNITY
          </p>
          <h2 className="text-4xl md:text-5xl font-extrabold text-[#1A3A37] mb-4 leading-tight">
            You’re Not Alone <br /> on This Journey
          </h2>
          <p className="text-gray-600 text-lg mb-6 max-w-md">
            Connect with others, share experiences, and find encouragement in a
            safe, supportive space.
          </p>
          <button className="px-8 py-3 bg-[#1A3A37] hover:bg-[#154F4A] text-white font-medium rounded-full text-sm transition-all duration-200 shadow-md">
            Join The Community
          </button>
        </div>

        <div className="flex-1 flex justify-end mt-10 md:mt-0">
          <img
            src={CommunityIllustration}
            alt="Community Illustration"
            className="w-[350px] h-auto"
          />
        </div>
      </section>

      {/* Resources Section */}
      <section
        id="resources"
        className="w-[90%] max-w-[1200px] text-center py-24 border-t border-gray-100"
      >
        <p className="text-sm tracking-wider text-gray-500 font-semibold mb-3">
          EXPLORE & LEARN
        </p>
        <h2 className="text-4xl md:text-5xl font-extrabold text-[#1A3A37] mb-4 leading-tight">
          Resources for <br className="hidden md:block" /> Your Well-being
        </h2>
        <p className="text-gray-600 text-lg max-w-2xl mx-auto mb-16">
          Explore expert insights, self-care guides, and tools to support your
          mental health.
        </p>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Articles & Guides Card */}
          <div className="bg-white border border-gray-200 rounded-3xl p-10 text-left flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="z-10">
              <h3 className="text-2xl font-bold text-[#1A3A37] mb-3">
                Articles & Guides
              </h3>
              <p className="text-gray-700 mb-6">
                Practical tips on stress management, mindfulness, and emotional
                resilience.
              </p>
              <button className="px-6 py-2 border border-[#1A3A37] text-[#1A3A37] font-medium rounded-full text-sm hover:bg-[#1A3A37] hover:text-white transition-all duration-200">
                Explore
              </button>
            </div>
          </div>

          {/* Meditation & Relaxation Card */}
          <div className="bg-white border border-gray-200 rounded-3xl p-10 text-left flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="z-10">
              <h3 className="text-2xl font-bold text-[#1A3A37] mb-3">
                Meditation & Relaxation
              </h3>
              <p className="text-gray-700 mb-6">
                Audio sessions for guided meditation and deep breathing
                exercises.
              </p>
              <button className="px-6 py-2 border border-[#1A3A37] text-[#1A3A37] font-medium rounded-full text-sm hover:bg-[#1A3A37] hover:text-white transition-all duration-200">
                Explore
              </button>
            </div>
          </div>

          {/* Webinars & Workshops Card */}
          <div className="bg-white border border-gray-200 rounded-3xl p-10 text-left flex flex-col justify-between shadow-sm relative overflow-hidden">
            <div className="z-10">
              <h3 className="text-2xl font-bold text-[#1A3A37] mb-3">
                Webinars & Workshops
              </h3>
              <p className="text-gray-700 mb-6">
                Live and recorded sessions with mental health professionals.
              </p>
              <button className="px-6 py-2 border border-[#1A3A37] text-[#1A3A37] font-medium rounded-full text-sm hover:bg-[#1A3A37] hover:text-white transition-all duration-200">
                Explore
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Login Modal */}
      {showLogin && (
        <div className="fixed inset-0 z-50">
          <LoginModal isOpen={showLogin} onClose={() => setShowLogin(false)} />
        </div>
      )}
    </div>
  );
};

export default LandingPage;

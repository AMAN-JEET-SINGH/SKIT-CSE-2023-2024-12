import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import calmingAnimation from "../assets/Breathe.json";

export default function Calming() {
  const navigate = useNavigate();
  const audioRef = useRef(null);
  const containerRef = useRef(null);
  const [lottieLoaded, setLottieLoaded] = useState(false);

  useEffect(() => {
    const audioElement = audioRef.current;

    // Auto-play audio when component mounts
    if (audioElement) {
      audioElement.play().catch((error) => {
        console.error("Audio playback failed:", error);
      });
    }

    return () => {
      // Stop audio when component unmounts
      if (audioElement) {
        audioElement.pause();
        audioElement.currentTime = 0;
      }
    };
  }, []);

  // Load lottie-web from CDN and render animation
  useEffect(() => {
    const loadAndRenderLottie = async () => {
      try {
        // Dynamically load lottie-web from CDN
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/lottie-web@5.12.2/build/player/lottie.min.js";
        script.async = true;
        
        script.onload = () => {
          // Wait for lottie to be available
          if (window.lottie && containerRef.current) {
            // Clear previous animation if any
            containerRef.current.innerHTML = "";
            
            window.lottie.loadAnimation({
              container: containerRef.current,
              renderer: "svg",
              loop: true,
              autoplay: true,
              animationData: calmingAnimation,
            });
            
            setLottieLoaded(true);
          }
        };
        
        script.onerror = () => {
          console.error("Failed to load lottie-web library");
        };
        
        document.head.appendChild(script);
      } catch (error) {
        console.error("Error loading Lottie:", error);
      }
    };

    // Only load if lottie-web is not already loaded
    if (!window.lottie) {
      loadAndRenderLottie();
    } else if (containerRef.current && !lottieLoaded) {
      // If lottie is already available, use it immediately
      containerRef.current.innerHTML = "";
      window.lottie.loadAnimation({
        container: containerRef.current,
        renderer: "svg",
        loop: true,
        autoplay: true,
        animationData: calmingAnimation,
      });
      setLottieLoaded(true);
    }
  }, [lottieLoaded]);

  const handleFeelBetter = () => {
    // Stop audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    // Navigate back to dashboard
    navigate("/dashboard");
  };

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-center p-6 relative overflow-hidden"
      style={{ backgroundColor: "#f5fbff" }}
    >
      {/* Solid Background with custom color */}
      <div
        className="absolute inset-0"
        style={{
          backgroundColor: "#61BDD3",
          opacity: 0.95,
        }}
      ></div>

      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute top-20 left-10 w-72 h-72 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.3)",
          }}
        ></div>
        <div
          className="absolute top-40 right-10 w-72 h-72 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.2)",
          }}
        ></div>
        <div
          className="absolute -bottom-8 left-20 w-72 h-72 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.25)",
          }}
        ></div>
      </div>

      {/* Main Content Container */}
      <div className="relative z-10 flex flex-col items-center justify-center max-w-2xl">
        {/* Lottie Animation Container */}
        <div
          ref={containerRef}
          className="w-full h-96 md:h-screen md:w-screen mb-8 flex items-center justify-center"
          style={{
            filter: "drop-shadow(0 0 20px rgba(255, 255, 255, 0.3))",
            maxWidth: "500px",
            maxHeight: "500px",
          }}
        ></div>

        

        {/* Audio Element */}
        <audio
          ref={audioRef}
          autoPlay
          loop
          style={{ display: "none" }}
        >
          <source src="/calming_audio.mp3" type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>

        {/* Feel Better Button */}
        <button
          onClick={handleFeelBetter}
          className="mt-8 px-8 py-4 bg-white text-[#61BDD3] text-lg font-semibold rounded-full shadow-2xl hover:shadow-3xl transform transition-all duration-300 hover:scale-105 active:scale-95"
        >
          I am Feeling Better
        </button>
      </div>

      <style>{`
        @keyframes blob {
          0%, 100% {
            transform: translate(0, 0) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
        }

        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fade-in-delayed {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-blob {
          animation: blob 7s infinite;
        }

        .animation-delay-2000 {
          animation-delay: 2s;
        }

        .animation-delay-4000 {
          animation-delay: 4s;
        }

        .animate-fade-in {
          animation: fade-in 1s ease-out;
        }

        .animate-fade-in-delayed {
          animation: fade-in-delayed 1s ease-out 0.3s both;
        }
      `}</style>
    </div>
  );
}

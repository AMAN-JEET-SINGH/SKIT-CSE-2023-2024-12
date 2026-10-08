import React, { useState, useRef, useEffect, useCallback } from "react";
import { toast } from "react-toastify";
import {
  Edit3,
  Video,
  Save,
  Play,
  Square,
  Calendar,
  Flame,
  FileText,
  VideoIcon,
  X,
  Download,
  Mic,
  Upload,
  Trash2,
  Shield,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function Progress() {
  const [journalText, setJournalText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [recordedVideoUrl, setRecordedVideoUrl] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [journalStreak, setJournalStreak] = useState(12);
  const [lastJournalDate, setLastJournalDate] = useState("Today");
  const [showVideoDialog, setShowVideoDialog] = useState(false);
  const [savedVideos, setSavedVideos] = useState([]);
  const [pendingStream, setPendingStream] = useState(null);
  const [privacyMode, setPrivacyMode] = useState("anonymized"); // "anonymized" or "full_privacy"
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState("");
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  const [textPrivacyMode, setTextPrivacyMode] = useState("anonymized");
  const [isAnalyzingText, setIsAnalyzingText] = useState(false);
  const videoRef = useRef(null);
  const previewRef = useRef(null);
  const fileInputRef = useRef(null);
  const analysisResultRef = useRef(null);
  const { user, getAuthHeaders } = useAuth();
  const [journalStats, setJournalStats] = useState({
    total_entries: 0,
    text_entries: 0,
    video_entries: 0,
    current_streak: 0,
    longest_streak: 0,
    last_entry_date: null,
  });
  const [journalEntries, setJournalEntries] = useState([]);
  const [journalEntriesLoading, setJournalEntriesLoading] = useState(true);
  const [journalEntriesError, setJournalEntriesError] = useState("");

  const fetchJournalStats = useCallback(async () => {
    try {
      const response = await fetch("http://localhost:8000/api/journals/stats", {
        headers: {
          ...getAuthHeaders(),
        },
      });

      if (response.ok) {
        const data = await response.json();
        setJournalStats(data.stats);
      }
    } catch (error) {
      console.error("Failed to fetch journal stats:", error);
    }
  }, [getAuthHeaders]);

  const fetchJournalEntries = useCallback(async () => {
    try {
      setJournalEntriesLoading(true);
      const response = await fetch(
        "http://localhost:8000/api/journals/my-journals?limit=100",
        { headers: { ...getAuthHeaders() } }
      );

      if (!response.ok) {
        throw new Error(`Journal history request failed: ${response.statusText}`);
      }

      const data = await response.json();
      setJournalEntries(Array.isArray(data.journals) ? data.journals : []);
      setJournalEntriesError("");
    } catch (error) {
      console.error("Failed to fetch journal entries:", error);
      setJournalEntriesError("Journal history could not be loaded.");
    } finally {
      setJournalEntriesLoading(false);
    }
  }, [getAuthHeaders]);

  const startVideoRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: true,
      });

      // Store stream temporarily until dialog opens
      setPendingStream(stream);
      setShowVideoDialog(true);
    } catch (error) {
      console.error("Error accessing camera:", error);
      alert(
        "Unable to access camera and microphone. Please check permissions."
      );
    }
  };

  // Wait until dialog and video element are mounted before starting recording
  useEffect(() => {
    if (showVideoDialog && pendingStream && videoRef.current) {
      // Attach live preview
      videoRef.current.srcObject = pendingStream;

      const recorder = new MediaRecorder(pendingStream, {
        mimeType: "video/webm;codecs=vp9,opus",
      });
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "video/webm" });
        const videoUrl = URL.createObjectURL(blob);
        setRecordedVideoUrl(videoUrl);

        const fileName = `journal-${
          new Date().toISOString().split("T")[0]
        }-${Date.now()}.webm`;

        // Download the video locally
        const link = document.createElement("a");
        link.href = videoUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setSavedVideos((prev) => [
          ...prev,
          {
            id: Date.now(),
            url: videoUrl,
            timestamp: new Date(),
            name: fileName,
            size: blob.size,
          },
        ]);

        // Show initial success toast
        toast.success("Video journal recorded and downloaded successfully!", {
          position: "top-right",
          autoClose: 3000,
          hideProgressBar: false,
          closeOnClick: true,
          pauseOnHover: true,
        });

        // Clean up stream and close dialog
        pendingStream.getTracks().forEach((t) => t.stop());
        if (videoRef.current) videoRef.current.srcObject = null;
        setShowVideoDialog(false);
        setPendingStream(null);

        // Now upload the recorded video to the API for analysis
        try {
          setIsAnalyzing(true);
          setAnalysisProgress("Uploading video...");

          // Create a File object from the blob
          const file = new File([blob], fileName, { type: "video/webm" });

          const formData = new FormData();
          formData.append("file", file);
          formData.append("privacy_mode", privacyMode);
          formData.append("interval_seconds", 5);
          formData.append("frame_skip", 2);

          // Simulate progress updates
          const progressInterval = setInterval(() => {
            setAnalysisProgress((prev) => {
              const stages = [
                "Uploading video...",
                "Processing video frames...",
                "Analyzing facial expressions...",
                "Extracting audio...",
                "Transcribing speech...",
                "Analyzing audio emotions...",
                "Processing text sentiment...",
                "Generating AI assessment...",
                "Finalizing results...",
              ];
              const currentIndex = stages.indexOf(prev);
              if (currentIndex < stages.length - 1) {
                return stages[currentIndex + 1];
              }
              return prev;
            });
          }, 8000);

          const response = await fetch("http://localhost:8000/api/upload-video", {
            method: "POST",
            headers: {
              ...getAuthHeaders(),
            },
            body: formData,
          });

          clearInterval(progressInterval);

          if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
          }

          const result = await response.json();

          toast.success("Analysis completed and saved!", {
            position: "top-right",
            autoClose: 5000,
          });

          console.log("Complete Analysis Result:", result);
          displayAnalysisResults(result);

          // Refresh stats
          await Promise.all([fetchJournalStats(), fetchJournalEntries()]);

          setIsAnalyzing(false);
          setAnalysisProgress("");
        } catch (error) {
          console.error("Upload failed:", error);
          toast.error("Upload or analysis failed. Please try again.", {
            position: "top-right",
            autoClose: 5000,
          });
          setIsAnalyzing(false);
          setAnalysisProgress("");
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    }
  }, [showVideoDialog, pendingStream, privacyMode, getAuthHeaders, fetchJournalStats, fetchJournalEntries]);

  const stopVideoRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const closeVideoDialog = () => {
    if (isRecording) {
      stopVideoRecording();
    } else {
      setShowVideoDialog(false);
    }
  };

  // Fetch journal stats on component mount
  useEffect(() => {
    fetchJournalStats();
    fetchJournalEntries();
  }, [fetchJournalStats, fetchJournalEntries]);

  useEffect(() => {
    if (latestAnalysis) {
      analysisResultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [latestAnalysis]);

  const saveJournalEntry = async () => {
    if (journalText.trim()) {
      try {
        setIsAnalyzingText(true);

        const response = await fetch(
          "http://localhost:8000/api/analyze-text-journal",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...getAuthHeaders(),
            },
            body: JSON.stringify({
              text: journalText,
              privacy_mode: textPrivacyMode,
            }),
          }
        );

        if (!response.ok) {
          throw new Error(`Analysis failed: ${response.statusText}`);
        }

        const result = await response.json();

        toast.success("Journal analyzed and saved successfully!", {
          position: "top-right",
          autoClose: 3000,
        });

        // Display results
        console.log("Text Journal Analysis:", result);
        displayTextAnalysisResults(result);

        // Refresh stats
        await Promise.all([fetchJournalStats(), fetchJournalEntries()]);

        // Clear form
        setJournalText("");
        setIsAnalyzingText(false);
      } catch (error) {
        console.error("Text journal analysis failed:", error);
        toast.error("Failed to analyze journal entry.", {
          position: "top-right",
          autoClose: 5000,
        });
        setIsAnalyzingText(false);
      }
    }
  };

  const displayTextAnalysisResults = (result) => {
    setLatestAnalysis({ kind: "text", result });
  };

  const handleVideoUpload = async (e) => {
    const files = Array.from(e.target.files);

    for (const file of files) {
      if (file.type.startsWith("video/")) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("privacy_mode", privacyMode);
        formData.append("interval_seconds", 5);
        formData.append("frame_skip", 2);

        try {
          setIsAnalyzing(true);
          setAnalysisProgress("Uploading video...");

          // Simulate progress updates
          const progressInterval = setInterval(() => {
            setAnalysisProgress((prev) => {
              const stages = [
                "Uploading video...",
                "Processing video frames...",
                "Analyzing facial expressions...",
                "Extracting audio...",
                "Transcribing speech...",
                "Analyzing audio emotions...",
                "Processing text sentiment...",
                "Generating AI assessment...",
                "Finalizing results...",
              ];
              const currentIndex = stages.indexOf(prev);
              if (currentIndex < stages.length - 1) {
                return stages[currentIndex + 1];
              }
              return prev;
            });
          }, 8000);

          const response = await fetch("http://localhost:8000/api/upload-video", {
            method: "POST",
            headers: {
              ...getAuthHeaders(),
            },
            body: formData,
          });

          clearInterval(progressInterval);

          if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
          }

          const result = await response.json();

          toast.success("Analysis completed and saved!", {
            position: "top-right",
            autoClose: 5000,
          });

          console.log("Complete Analysis Result:", result);
          displayAnalysisResults(result);

          // Refresh stats
          await Promise.all([fetchJournalStats(), fetchJournalEntries()]);

          setIsAnalyzing(false);
          setAnalysisProgress("");
        } catch (error) {
          console.error("Upload failed:", error);
          toast.error("Upload or analysis failed. Please try again.", {
            position: "top-right",
            autoClose: 5000,
          });
          setIsAnalyzing(false);
          setAnalysisProgress("");
        }
      }
    }
  };

  const displayAnalysisResults = (result) => {
    setLatestAnalysis({ kind: "video", result });
  };

  const deleteVideo = (videoId) => {
    setSavedVideos((prev) => prev.filter((v) => v.id !== videoId));

    toast.info("Video removed from list", {
      position: "top-right",
      autoClose: 2000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const analysis = latestAnalysis?.result;
  const scoreMetrics = analysis
    ? [
        { label: "Mental health", value: analysis.mental_health_score },
        { label: "Depression", value: analysis.depression_score },
        { label: "Anxiety", value: analysis.anxiety_score },
        { label: "Stress", value: analysis.stress_score },
      ]
    : [];
  const journalEntriesByDay = journalEntries.reduce((entriesByDay, entry) => {
    const day = entry.date?.slice(0, 10) || entry.timestamp?.slice(0, 10) || "Unknown date";
    entriesByDay[day] ??= [];
    entriesByDay[day].push(entry);
    return entriesByDay;
  }, {});

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#1A3A37] mb-2">
            Your Journal
          </h1>
          <p className="text-gray-600">
            Reflect on your thoughts and record your daily experiences
          </p>
        </div>

        {/* Stats Row - Use Real Data */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* Streak Card */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-orange-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <Flame className="w-6 h-6 text-orange-500" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {journalStats.current_streak}
            </h3>
            <p className="text-gray-600 text-sm font-medium">Day Streak</p>
            <p className="text-orange-500 text-xs mt-1">Keep it up!</p>
          </div>

          {/* Text Entries */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-green-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <FileText className="w-6 h-6 text-green-600" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {journalStats.text_entries}
            </h3>
            <p className="text-gray-600 text-sm font-medium">Text Entries</p>
            <p className="text-green-600 text-xs mt-1">Keep writing!</p>
          </div>

          {/* Video Journals */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-blue-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <VideoIcon className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {journalStats.video_entries}
            </h3>
            <p className="text-gray-600 text-sm font-medium">Video Journals</p>
            <p className="text-blue-600 text-xs mt-1">Share your story!</p>
          </div>

          {/* Total Entries */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-purple-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <Calendar className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {journalStats.total_entries}
            </h3>
            <p className="text-gray-600 text-sm font-medium">Total Entries</p>
            <p className="text-purple-600 text-xs mt-1">Amazing progress!</p>
          </div>
        </div>

        {analysis && (
          <section
            ref={analysisResultRef}
            aria-live="polite"
            className="scroll-mt-6 rounded-2xl border border-green-200 bg-white p-6 shadow-sm"
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-green-700">
                  {latestAnalysis.kind === "video" ? "Video journal" : "Text journal"}
                </p>
                <h2 className="text-xl font-bold text-[#1A3A37]">Analysis results</h2>
                <p className="mt-1 text-sm text-gray-600">
                  These results offer general insight and are not a diagnosis.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setLatestAnalysis(null)}
                aria-label="Dismiss analysis results"
                className="rounded-full p-2 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-800"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {scoreMetrics.map(({ label, value }) => (
                <div key={label} className="rounded-xl bg-gray-50 p-4">
                  <p className="text-sm text-gray-600">{label}</p>
                  <p className="mt-1 text-2xl font-bold text-[#1A3A37]">
                    {typeof value === "number" ? `${value}/100` : "—"}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-xs font-medium uppercase text-gray-500">Risk level</p>
                <p className="mt-1 font-semibold capitalize text-gray-900">{analysis.risk_level || "Unknown"}</p>
              </div>
              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-xs font-medium uppercase text-gray-500">Dominant emotion</p>
                <p className="mt-1 font-semibold capitalize text-gray-900">
                  {analysis.dominant_emotion || analysis.text_emotion || analysis.audio_emotion || analysis.video_emotion || "Unknown"}
                </p>
              </div>
              <div className="rounded-xl border border-gray-200 p-4">
                <p className="text-xs font-medium uppercase text-gray-500">Confidence</p>
                <p className="mt-1 font-semibold text-gray-900">
                  {typeof analysis.confidence === "number" ? `${Math.round(analysis.confidence * 100)}%` : "—"}
                </p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-1 gap-5 md:grid-cols-2">
              {[
                ["Key indicators", analysis.key_indicators],
                ["Areas of concern", analysis.areas_of_concern],
                ["Positive indicators", analysis.positive_indicators],
                ["Recommendations", analysis.recommendations],
              ].map(([title, items]) =>
                Array.isArray(items) && items.length > 0 ? (
                  <div key={title}>
                    <h3 className="mb-2 font-semibold text-[#1A3A37]">{title}</h3>
                    <ul className="list-inside list-disc space-y-1 text-sm leading-relaxed text-gray-700">
                      {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
                    </ul>
                  </div>
                ) : null
              )}
            </div>
          </section>
        )}

        <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-[#1A3A37]">Journal by day</h2>
              <p className="mt-1 text-sm text-gray-600">
                Your saved analysis results, grouped by journal date
              </p>
            </div>
            <span className="text-sm text-gray-500">
              {journalEntries.length} {journalEntries.length === 1 ? "entry" : "entries"}
            </span>
          </div>

          {journalEntriesLoading ? (
            <p className="text-sm text-gray-500">Loading your journal history...</p>
          ) : journalEntriesError ? (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p role="alert" className="text-sm text-red-700">{journalEntriesError}</p>
              <button
                type="button"
                onClick={fetchJournalEntries}
                className="text-sm font-medium text-[#1A3A37] underline underline-offset-2"
              >
                Try again
              </button>
            </div>
          ) : journalEntries.length === 0 ? (
            <p className="text-sm text-gray-500">
              Your saved analysis results will appear here after you write or upload a journal.
            </p>
          ) : (
            <div className="space-y-6">
              {Object.entries(journalEntriesByDay)
                .sort(([firstDay], [secondDay]) => secondDay.localeCompare(firstDay))
                .map(([day, entries]) => (
                  <div key={day}>
                    <div className="mb-3 flex items-center gap-3">
                      <h3 className="font-semibold text-gray-900">
                        {day === "Unknown date"
                          ? day
                          : new Date(`${day}T00:00:00`).toLocaleDateString(undefined, {
                              weekday: "long",
                              year: "numeric",
                              month: "long",
                              day: "numeric",
                            })}
                      </h3>
                      <span className="text-xs text-gray-500">
                        {entries.length} {entries.length === 1 ? "entry" : "entries"}
                      </span>
                    </div>

                    <div className="space-y-3">
                      {entries.map((entry) => {
                        const assessment = entry.llm_assessment || {};
                        const emotions = entry.emotion_analysis || {};
                        const depression = entry.depression_analysis || {};
                        const metrics = [
                          ["Mental health", assessment.mental_health_score ?? assessment.overall_mental_health_score],
                          ["Depression", assessment.depression_score],
                          ["Anxiety", assessment.anxiety_score],
                          ["Stress", assessment.stress_score],
                        ];
                        const indicators = Array.isArray(assessment.key_indicators)
                          ? assessment.key_indicators
                          : [];
                        const recommendations = Array.isArray(assessment.recommendations)
                          ? assessment.recommendations
                          : [];

                        return (
                          <article key={entry._id} className="rounded-xl border border-gray-200 p-4">
                            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                              <p className="font-medium capitalize text-[#1A3A37]">
                                {entry.journal_type || "Journal"} journal
                              </p>
                              <p className="text-xs text-gray-500">
                                {entry.timestamp
                                  ? new Date(entry.timestamp).toLocaleTimeString([], {
                                      hour: "numeric",
                                      minute: "2-digit",
                                    })
                                  : ""}
                              </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                              {metrics.map(([label, value]) => (
                                <div key={label} className="rounded-lg bg-gray-50 px-3 py-2">
                                  <p className="text-xs text-gray-500">{label}</p>
                                  <p className="font-semibold text-gray-900">
                                    {value == null ? "—" : `${value}/100`}
                                  </p>
                                </div>
                              ))}
                            </div>

                            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-gray-600">
                              <span>
                                Emotion: <strong className="capitalize text-gray-900">
                                  {emotions.dominant_emotion || emotions.text_emotion || emotions.audio_emotion || "Unknown"}
                                </strong>
                              </span>
                              <span>
                                Risk: <strong className="capitalize text-gray-900">
                                  {assessment.risk_level || "Unknown"}
                                </strong>
                              </span>
                              <span>
                                Depression level: <strong className="capitalize text-gray-900">
                                  {depression.depression_level || "Unknown"}
                                </strong>
                              </span>
                            </div>

                            {(indicators.length > 0 || recommendations.length > 0) && (
                              <details className="mt-3 border-t border-gray-100 pt-3">
                                <summary className="cursor-pointer text-sm font-medium text-[#1A3A37]">
                                  View indicators and recommendations
                                </summary>
                                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                                  {indicators.length > 0 && (
                                    <div>
                                      <h4 className="mb-1 text-sm font-semibold text-gray-800">Key indicators</h4>
                                      <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                                        {indicators.map((item, index) => <li key={`indicator-${index}`}>{item}</li>)}
                                      </ul>
                                    </div>
                                  )}
                                  {recommendations.length > 0 && (
                                    <div>
                                      <h4 className="mb-1 text-sm font-semibold text-gray-800">Recommendations</h4>
                                      <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                                        {recommendations.map((item, index) => <li key={`recommendation-${index}`}>{item}</li>)}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              </details>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </section>

        {/* Text Journal Section */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-green-50 p-3 rounded-xl">
              <Edit3 className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#1A3A37]">
                Write Your Thoughts
              </h2>
              <p className="text-gray-600 text-sm">
                Take a moment to reflect on your day and feelings
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Privacy Mode Toggle */}
            <div className="bg-linear-to-r from-green-50 to-teal-50 rounded-xl p-4 border border-green-200 mb-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {textPrivacyMode === "full_privacy" ? (
                    <ShieldCheck className="w-5 h-5 text-purple-600" />
                  ) : (
                    <Shield className="w-5 h-5 text-green-600" />
                  )}
                  <h3 className="text-base font-semibold text-gray-800">
                    Privacy Mode
                  </h3>
                </div>
                <button
                  onClick={() =>
                    setTextPrivacyMode((prev) =>
                      prev === "anonymized" ? "full_privacy" : "anonymized"
                    )
                  }
                  className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors ${
                    textPrivacyMode === "full_privacy"
                      ? "bg-purple-600"
                      : "bg-green-500"
                  }`}
                >
                  <span
                    className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                      textPrivacyMode === "full_privacy"
                        ? "translate-x-9"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="text-xs text-gray-600">
                {textPrivacyMode === "anonymized" ? (
                  <p>Names and personal details will be anonymized before analysis</p>
                ) : (
                  <p>Maximum privacy - only emotion/depression scores sent to LLM</p>
                )}
              </div>
            </div>

            <textarea
              value={journalText}
              onChange={(e) => setJournalText(e.target.value)}
              placeholder="Dear journal, today I feel... What's been on my mind? How did my day go? Take your time to express your thoughts..."
              className="w-full h-64 p-4 border border-gray-300 rounded-xl resize-none focus:outline-none focus:border-[#1A3A37] focus:ring-1 focus:ring-[#1A3A37] text-sm leading-relaxed"
            />

            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-500">
                {journalText.length} characters
              </p>
              <button
                onClick={saveJournalEntry}
                disabled={!journalText.trim() || isAnalyzingText}
                className="flex items-center gap-2 bg-[#1A3A37] text-white px-6 py-2 rounded-full font-medium hover:bg-[#154F4A] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
              >
                {isAnalyzingText ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Entry
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Video Journal Section */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-blue-50 p-3 rounded-xl">
              <Video className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#1A3A37]">
                Video Journal
              </h2>
              <p className="text-gray-600 text-sm">
                Record yourself talking about your day and experiences
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Privacy Mode Toggle */}
            <div className="bg-linear-to-r from-blue-50 to-purple-50 rounded-xl p-4 border border-blue-200">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {privacyMode === "full_privacy" ? (
                    <ShieldCheck className="w-5 h-5 text-purple-600" />
                  ) : (
                    <Shield className="w-5 h-5 text-blue-600" />
                  )}
                  <h3 className="text-base font-semibold text-gray-800">
                    Privacy Mode
                  </h3>
                </div>
                <button
                  onClick={() =>
                    setPrivacyMode((prev) =>
                      prev === "anonymized" ? "full_privacy" : "anonymized"
                    )
                  }
                  className={`relative inline-flex h-8 w-16 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                    privacyMode === "full_privacy"
                      ? "bg-purple-600 focus:ring-purple-500"
                      : "bg-blue-500 focus:ring-blue-400"
                  }`}
                >
                  <span
                    className={`inline-block h-6 w-6 transform rounded-full bg-white transition-transform ${
                      privacyMode === "full_privacy"
                        ? "translate-x-9"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <div className="space-y-2">
                {privacyMode === "anonymized" ? (
                  <div className="flex items-start gap-2">
                    <div className="bg-blue-100 p-1.5 rounded-lg shrink-0 mt-0.5">
                      <Shield className="w-4 h-4 text-blue-700" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-blue-900">
                        Anonymized Mode (Recommended)
                      </p>
                      <p className="text-xs text-blue-700 leading-relaxed mt-1">
                        Your data is processed with personal identifiers removed.
                        Names, locations, and specific details are anonymized while
                        preserving emotional context for analysis.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-2">
                    <div className="bg-purple-100 p-1.5 rounded-lg shrink-0 mt-0.5">
                      <ShieldCheck className="w-4 h-4 text-purple-700" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-purple-900">
                        Full Privacy Mode
                      </p>
                      <p className="text-xs text-purple-700 leading-relaxed mt-1">
                        Maximum privacy protection. All personal information is
                        completely removed before analysis. Only general emotional
                        patterns are evaluated with no identifying data retained.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-blue-200">
                <p className="text-xs text-gray-600 flex items-center gap-1">
                  <span className="font-semibold">Current Mode:</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      privacyMode === "full_privacy"
                        ? "bg-purple-200 text-purple-800"
                        : "bg-blue-200 text-blue-800"
                    }`}
                  >
                    {privacyMode === "full_privacy"
                      ? "Full Privacy"
                      : "Anonymized"}
                  </span>
                </p>
              </div>
            </div>

            {/* Video Recording Preview / Loader */}
            <div className="bg-gray-100 rounded-xl overflow-hidden">
              <div className="h-64 flex items-center justify-center">
                {isAnalyzing ? (
                  <div className="text-center">
                    <div className="relative mb-6">
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-24 h-24 border-8 border-blue-100 rounded-full"></div>
                      </div>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-24 h-24 border-8 border-t-blue-600 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
                      </div>
                      <div className="relative z-10 flex items-center justify-center w-24 h-24 mx-auto">
                        <Video className="w-10 h-10 text-blue-600" />
                      </div>
                    </div>
                    <h3 className="text-lg font-bold text-gray-800 mb-2">
                      Analyzing Your Video
                    </h3>
                    <p className="text-gray-600 text-sm mb-4 max-w-md">
                      {analysisProgress}
                    </p>
                    <div className="bg-white rounded-full p-2 inline-flex items-center gap-2 shadow-sm">
                      <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                      <span className="text-xs text-gray-600 font-medium pr-2">
                        This may take a few minutes...
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-center">
                    <Video className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">
                      Ready to record your video journal
                    </p>
                    <p className="text-gray-500 text-sm">
                      Click start to begin recording with audio and video
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Video Controls */}
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-500">
                {isAnalyzing ? (
                  <span className="flex items-center gap-2 text-blue-600 font-medium">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analysis in progress...
                  </span>
                ) : (
                  "HD Video Recording • High Quality Audio • Auto Download"
                )}
              </div>

              <div className="flex gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/*"
                  onChange={handleVideoUpload}
                  className="hidden"
                  multiple
                  disabled={isAnalyzing}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isAnalyzing}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-colors ${
                    isAnalyzing
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-blue-500 text-white hover:bg-blue-600"
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  Upload Video
                </button>
                <button
                  onClick={startVideoRecording}
                  disabled={isAnalyzing}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full font-medium transition-colors ${
                    isAnalyzing
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-red-500 text-white hover:bg-red-600"
                  }`}
                >
                  <Play className="w-4 h-4" />
                  Start Recording
                </button>
              </div>
            </div>

            {/* Recent Videos */}
            {savedVideos.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-[#1A3A37] mb-4">
                  Recent Video Journals ({savedVideos.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {savedVideos.slice(-6).map((video) => (
                    <div
                      key={video.id}
                      className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className="bg-blue-50 p-2 rounded-lg shrink-0">
                          <VideoIcon className="w-4 h-4 text-blue-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-700 truncate">
                            {video.name}
                          </p>
                          <p className="text-xs text-gray-500">
                            {video.timestamp.toLocaleDateString()}{" "}
                            {video.timestamp.toLocaleTimeString()}
                          </p>
                          {video.size && (
                            <p className="text-xs text-gray-400 mt-1">
                              {formatFileSize(video.size)}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => deleteVideo(video.id)}
                          className="text-gray-400 hover:text-red-500 transition-colors shrink-0"
                          title="Remove video"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Video Recording Dialog */}
        {showVideoDialog && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-3xl overflow-hidden shadow-2xl max-w-5xl w-full max-h-[90vh]">
              {/* Dialog Header - Minimalist */}
              {/* <div className="bg-[#1A3A37] p-6 text-white flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="bg-white/20 p-3 rounded-xl">
                    <Video className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="text-2xl font-bold">
                      Video Journal Recording
                    </h3>
                    <p className="text-gray-200 text-sm">
                      Express yourself freely and capture your thoughts
                    </p>
                  </div>
                </div>
                <button
                  onClick={closeVideoDialog}
                  className="bg-white/20 hover:bg-white/30 p-3 rounded-full transition-colors shrink-0"
                >
                  <X className="w-6 h-6" />
                </button>
              </div> */}

              {/* Video Feed */}
              <div className="relative bg-gray-900">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  className="w-full h-[500px] object-cover"
                />

                {/* Recording Indicator - Minimalist */}
                {isRecording && (
                  <div className="absolute top-6 left-6 bg-red-500 text-white px-4 py-2 rounded-full text-base font-bold flex items-center gap-3 shadow-lg">
                    <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                    RECORDING
                  </div>
                )}

                {/* Audio Indicator - Minimalist */}
                {isRecording && (
                  <div className="absolute top-6 right-6 bg-green-500 text-white px-4 py-2 rounded-full text-base font-bold flex items-center gap-2 shadow-lg">
                    <Mic className="w-5 h-5" />
                    AUDIO
                  </div>
                )}

                {/* Recording Status */}
                {isRecording && (
                  <div className="absolute bottom-6 left-6 bg-black/60 text-white px-4 py-2 rounded-full text-sm font-medium">
                    Recording...
                  </div>
                )}
              </div>

              {/* Controls - Minimalist */}
              <div className="p-3 bg-white flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  {isRecording ? (
                    <span className="font-semibold">
                      🔴 Recording in progress... Click "Stop & Save" when
                      you're done
                    </span>
                  ) : null}
                </div>

                {isRecording && (
                  <button
                    onClick={stopVideoRecording}
                    className="flex items-center gap-2 bg-gray-800 text-white px-4 py-2 rounded-full text-base font-semibold hover:bg-gray-900 transition-colors shadow-lg"
                  >
                    <Square className="w-5 h-5" />
                    Stop & Save
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
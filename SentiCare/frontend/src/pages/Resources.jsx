import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingDown,
  TrendingUp,
  Brain,
  Heart,
  Shield,
  BookOpen,
  Target,
  Calendar,
  Star,
  User,
  Activity,
  Lightbulb,
  Loader2,
  X,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

export default function Resources() {
  const { getAuthHeaders } = useAuth();
  const navigate = useNavigate();
  const [progressData, setProgressData] = useState([]);
  const [journals, setJournals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAlertDialog, setShowAlertDialog] = useState(false);
  const [alertMessage, setAlertMessage] = useState({
    title: "",
    description: "",
    highParameters: [],
  });
  const [stats, setStats] = useState({
    depressionImprovement: 0,
    stressImprovement: 0,
    anxietyImprovement: 0,
    bestTime: "Morning",
    weekendImprovement: 0,
  });

  useEffect(() => {
    fetchJournalData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchJournalData = async () => {
    try {
      setLoading(true);

      // Fetch user's journal entries (last 50)
      const response = await fetch(
        "http://localhost:8000/api/journals/my-journals?limit=50",
        {
          headers: {
            ...getAuthHeaders(),
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setJournals(data.journals);
        processJournalData(data.journals);
      }
    } catch (error) {
      console.error("Failed to fetch journal data:", error);
    } finally {
      setLoading(false);
    }
  };

  const checkHighScores = (journalEntries) => {
    // Check if user has dismissed the alert
    const dismissed = localStorage.getItem("mentalHealthAlertDismissed");
    if (dismissed === "true") {
      return;
    }

    if (!journalEntries || journalEntries.length < 2) {
      return;
    }

    // Group journals by date and sort
    const journalsByDate = {};
    journalEntries.forEach((journal) => {
      const date = journal.date;
      if (!journalsByDate[date]) {
        journalsByDate[date] = [];
      }
      journalsByDate[date].push(journal);
    });

    // Get last 2 days of data
    const sortedDates = Object.keys(journalsByDate).sort();
    if (sortedDates.length < 2) {
      return;
    }

    const lastTwoDates = sortedDates.slice(-2);
    
    // Calculate average scores for each day
    const dailyScores = lastTwoDates.map(date => {
      const dayJournals = journalsByDate[date];
      const avgDepression = dayJournals.reduce(
        (sum, j) => sum + (j.llm_assessment?.depression_score || j.depression_score || 0),
        0
      ) / dayJournals.length;
      const avgStress = dayJournals.reduce(
        (sum, j) => sum + (j.llm_assessment?.stress_score || j.stress_score || 0),
        0
      ) / dayJournals.length;
      const avgAnxiety = dayJournals.reduce(
        (sum, j) => sum + (j.llm_assessment?.anxiety_score || j.anxiety_score || 0),
        0
      ) / dayJournals.length;

      return {
        depression: avgDepression,
        stress: avgStress,
        anxiety: avgAnxiety,
      };
    });

    // Check if scores meet alert criteria for both days
    const highParameters = [];
    let allThreeHigh = true;

    // Check if any parameter is above 80% for both days
    if (dailyScores[0].depression > 80 && dailyScores[1].depression > 80) {
      highParameters.push("Depression");
    }
    if (dailyScores[0].stress > 80 && dailyScores[1].stress > 80) {
      highParameters.push("Stress");
    }
    if (dailyScores[0].anxiety > 80 && dailyScores[1].anxiety > 80) {
      highParameters.push("Anxiety");
    }

    // Check if all three are above 50% for both days
    const day1AllHigh = dailyScores[0].depression > 50 && dailyScores[0].stress > 50 && dailyScores[0].anxiety > 50;
    const day2AllHigh = dailyScores[1].depression > 50 && dailyScores[1].stress > 50 && dailyScores[1].anxiety > 50;
    
    allThreeHigh = day1AllHigh && day2AllHigh;

    // Show alert if criteria met
    if (highParameters.length > 0 || allThreeHigh) {
      if (highParameters.length > 0) {
        setAlertMessage({
          title: "We're Concerned About You",
          description: `Your ${highParameters.join(", ")} levels have been elevated for the past 2 days. Taking time for self-care can make a real difference.`,
          highParameters: highParameters,
        });
      } else if (allThreeHigh) {
        setAlertMessage({
          title: "Your Mental Health Needs Attention",
          description: "Your overall mental health scores have been concerning for the past 2 days. It's important to take care of yourself.",
          highParameters: ["Depression", "Stress", "Anxiety"],
        });
      }
      setShowAlertDialog(true);
    }
  };

  const processJournalData = (journalEntries) => {
    if (!journalEntries || journalEntries.length === 0) {
      // Use dummy data if no journals
      setProgressData(generateDummyData());
      return;
    }

    // Check for high scores before processing
    checkHighScores(journalEntries);

    // Group journals by date
    const journalsByDate = {};
    journalEntries.forEach((journal) => {
      const date = journal.date;
      if (!journalsByDate[date]) {
        journalsByDate[date] = [];
      }
      journalsByDate[date].push(journal);
    });

    // Calculate daily averages (last 15 days)
    const dates = Object.keys(journalsByDate).sort().slice(-15);
    const chartData = dates.map((date, index) => {
      const dayJournals = journalsByDate[date];
      const avgDepression =
        dayJournals.reduce(
          (sum, j) =>
            sum +
            (j.llm_assessment?.depression_score || j.depression_score || 0),
          0
        ) / dayJournals.length;
      const avgStress =
        dayJournals.reduce(
          (sum, j) => sum + (j.llm_assessment?.stress_score || j.stress_score || 0),
          0
        ) / dayJournals.length;
      const avgAnxiety =
        dayJournals.reduce(
          (sum, j) =>
            sum + (j.llm_assessment?.anxiety_score || j.anxiety_score || 0),
          0
        ) / dayJournals.length;

      // Convert 0-100 scores to 1-10 scale (inverted: 100 = 1, 0 = 10)
      return {
        day: `Day ${index + 1}`,
        date: new Date(date).toLocaleDateString(),
        depression: Math.round(10 - (avgDepression / 100) * 9),
        stress: Math.round(10 - (avgStress / 100) * 9),
        anxiety: Math.round(10 - (avgAnxiety / 100) * 9),
      };
    });

    setProgressData(chartData);

    // Calculate improvements
    if (chartData.length >= 2) {
      const first = chartData[0];
      const last = chartData[chartData.length - 1];

      const depressionImprovement = Math.round(
        ((first.depression - last.depression) / first.depression) * 100
      );
      const stressImprovement = Math.round(
        ((first.stress - last.stress) / first.stress) * 100
      );
      const anxietyImprovement = Math.round(
        ((first.anxiety - last.anxiety) / first.anxiety) * 100
      );

      // Analyze time patterns
      const hourlyStats = analyzeHourlyPatterns(journalEntries);
      const weekendStats = analyzeWeekendPattern(journalEntries);

      setStats({
        depressionImprovement: Math.max(0, depressionImprovement),
        stressImprovement: Math.max(0, stressImprovement),
        anxietyImprovement: Math.max(0, anxietyImprovement),
        bestTime: hourlyStats.bestTime,
        weekendImprovement: weekendStats,
      });
    }
  };

  const analyzeHourlyPatterns = (journals) => {
    const hourlyScores = {};

    journals.forEach((journal) => {
      const hour = new Date(journal.timestamp).getHours();
      const mentalHealthScore =
        journal.llm_assessment?.mental_health_score ||
        journal.mental_health_score ||
        50;

      if (!hourlyScores[hour]) {
        hourlyScores[hour] = { total: 0, count: 0 };
      }
      hourlyScores[hour].total += mentalHealthScore;
      hourlyScores[hour].count += 1;
    });

    // Find best performing time
    let bestHour = 0;
    let bestScore = 0;

    Object.keys(hourlyScores).forEach((hour) => {
      const avg = hourlyScores[hour].total / hourlyScores[hour].count;
      if (avg > bestScore) {
        bestScore = avg;
        bestHour = parseInt(hour);
      }
    });

    // Convert hour to time period
    if (bestHour >= 6 && bestHour < 12) return "Morning (6 AM - 12 PM)";
    if (bestHour >= 12 && bestHour < 17) return "Afternoon (12 PM - 5 PM)";
    if (bestHour >= 17 && bestHour < 21) return "Evening (5 PM - 9 PM)";
    return "Night (9 PM - 6 AM)";
  };

  const analyzeWeekendPattern = (journals) => {
    const weekdayScores = [];
    const weekendScores = [];

    journals.forEach((journal) => {
      const date = new Date(journal.timestamp);
      const day = date.getDay();
      const score =
        journal.llm_assessment?.mental_health_score ||
        journal.mental_health_score ||
        50;

      if (day === 0 || day === 6) {
        weekendScores.push(score);
      } else {
        weekdayScores.push(score);
      }
    });

    if (weekendScores.length === 0 || weekdayScores.length === 0) return 0;

    const weekdayAvg =
      weekdayScores.reduce((a, b) => a + b, 0) / weekdayScores.length;
    const weekendAvg =
      weekendScores.reduce((a, b) => a + b, 0) / weekendScores.length;

    return Math.round(((weekendAvg - weekdayAvg) / weekdayAvg) * 100);
  };

  const generateDummyData = () => {
    return [
      { day: "Day 1", depression: 7, stress: 8, anxiety: 9 },
      { day: "Day 2", depression: 6, stress: 7, anxiety: 8 },
      { day: "Day 3", depression: 6, stress: 6, anxiety: 7 },
      { day: "Day 4", depression: 5, stress: 6, anxiety: 6 },
      { day: "Day 5", depression: 5, stress: 5, anxiety: 6 },
      { day: "Day 6", depression: 4, stress: 5, anxiety: 5 },
      { day: "Day 7", depression: 4, stress: 4, anxiety: 5 },
      { day: "Day 8", depression: 3, stress: 4, anxiety: 4 },
      { day: "Day 9", depression: 3, stress: 3, anxiety: 4 },
      { day: "Day 10", depression: 2, stress: 3, anxiety: 3 },
      { day: "Day 11", depression: 2, stress: 2, anxiety: 3 },
      { day: "Day 12", depression: 2, stress: 2, anxiety: 2 },
      { day: "Day 13", depression: 1, stress: 2, anxiety: 2 },
      { day: "Day 14", depression: 1, stress: 1, anxiety: 1 },
      { day: "Day 15", depression: 1, stress: 1, anxiety: 1 },
    ];
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white p-6 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-teal-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your progress data...</p>
        </div>
      </div>
    );
  }

  // Use dummy data for improvements if no real data
  const depressionImprovement =
    stats.depressionImprovement ||
    (progressData.length > 0
      ? Math.round(
          ((progressData[0].depression -
            progressData[progressData.length - 1].depression) /
            progressData[0].depression) *
            100
        )
      : 86);

  const stressImprovement =
    stats.stressImprovement ||
    (progressData.length > 0
      ? Math.round(
          ((progressData[0].stress -
            progressData[progressData.length - 1].stress) /
            progressData[0].stress) *
            100
        )
      : 88);

  const anxietyImprovement =
    stats.anxietyImprovement ||
    (progressData.length > 0
      ? Math.round(
          ((progressData[0].anxiety -
            progressData[progressData.length - 1].anxiety) /
            progressData[0].anxiety) *
            100
        )
      : 89);

  // Helper function to get feedback based on improvement percentage
  const getImprovementFeedback = (improvement) => {
    if (improvement >= 50) {
      return { message: "Exceptional progress!", icon: TrendingDown, color: "text-green-600" };
    } else if (improvement >= 30) {
      return { message: "Great improvement!", icon: TrendingDown, color: "text-green-500" };
    } else if (improvement >= 15) {
      return { message: "Good progress!", icon: TrendingDown, color: "text-blue-500" };
    } else if (improvement >= 5) {
      return { message: "Keep going!", icon: TrendingDown, color: "text-blue-400" };
    } else if (improvement >= -5) {
      return { message: "Steady state", icon: TrendingUp, color: "text-gray-500" };
    } else if (improvement >= -15) {
      return { message: "Needs attention", icon: TrendingUp, color: "text-orange-500" };
    } else {
      return { message: "Consider support", icon: TrendingUp, color: "text-red-500" };
    }
  };

  // Get feedback for each metric
  const depressionFeedback = getImprovementFeedback(depressionImprovement);
  const stressFeedback = getImprovementFeedback(stressImprovement);
  const anxietyFeedback = getImprovementFeedback(anxietyImprovement);

  // Define actual resources with real links
  const recommendedActivities = [
    {
      title: "Morning Meditation",
      description: "Continue your 10-minute morning routine - it's showing great results!",
      duration: "10 min daily",
      effectiveness: "85% effective",
      icon: Star,
      iconBg: "bg-yellow-50",
      iconColor: "text-yellow-500",
      url: "https://www.headspace.com/meditation/meditation-for-beginners",
    },
    {
      title: "Evening Journaling",
      description: "Your journal entries are helping track emotional patterns.",
      duration: "15 min daily",
      effectiveness: `${journals.length} entries logged`,
      icon: Calendar,
      iconBg: "bg-green-50",
      iconColor: "text-green-500",
      url: "/dashboard/progress",
      internal: true,
    },
    {
      title: "Breathing Exercises",
      description: "Try the 4-7-8 technique when feeling anxious.",
      duration: "3-5 min sessions",
      effectiveness: "As needed",
      icon: Activity,
      iconBg: "bg-purple-50",
      iconColor: "text-purple-500",
      url: "/calming",
      internal: true,
    },
  ];

  const learningResources = [
    {
      title: "Cognitive Behavioral Therapy",
      description: "Learn CBT techniques to manage negative thought patterns.",
      progress: "6-part series",
      status: "Evidence-based",
      icon: Star,
      iconBg: "bg-yellow-50",
      iconColor: "text-yellow-500",
      url: "https://www.apa.org/ptsd-guideline/patients-and-families/cognitive-behavioral",
    },
    {
      title: "Mindfulness Guide",
      description: "Deepen your mindfulness practice with guided exercises.",
      progress: "Interactive guide",
      status: "12 exercises",
      icon: Brain,
      iconBg: "bg-blue-50",
      iconColor: "text-blue-500",
      url: "https://ggia.berkeley.edu/practice/mindful_breathing",
    },
    {
      title: "Stress Management",
      description: "Advanced techniques for handling stress triggers.",
      progress: "Comprehensive guide",
      status: "Research-backed",
      icon: Heart,
      iconBg: "bg-red-50",
      iconColor: "text-red-500",
      url: "https://www.mayoclinic.org/healthy-lifestyle/stress-management/in-depth/stress-relievers/art-20047257",
    },
  ];

  const personalInsights = [
    {
      title: "Best Performance",
      description: `Your mood is most stable during ${stats.bestTime}.`,
      detail: `Peak time: ${stats.bestTime}`,
      status: journals.length > 0 ? "Based on your data" : "Sample insight",
      icon: TrendingUp,
      iconBg: "bg-green-50",
      iconColor: "text-green-500",
      url: "https://www.sleepfoundation.org/circadian-rhythm",
    },
    {
      title: "Weekly Pattern",
      description: stats.weekendImprovement > 0
        ? `Weekends show ${stats.weekendImprovement}% improved stress levels - maintain this balance.`
        : "Keep tracking to identify your weekly patterns.",
      detail: "Weekend vs Weekday",
      status: stats.weekendImprovement > 0
        ? `${stats.weekendImprovement}% better`
        : "Analyzing...",
      icon: Calendar,
      iconBg: "bg-blue-50",
      iconColor: "text-blue-500",
      url: "https://www.apa.org/topics/work-life-balance",
    },
    {
      title: "Social Connections",
      description: "Social connections can boost your overall wellbeing.",
      detail: "Improvement area",
      status: "High impact",
      icon: Shield,
      iconBg: "bg-purple-50",
      iconColor: "text-purple-500",
      url: "https://www.mentalhealth.org.uk/explore-mental-health/a-z-topics/relationships",
    },
  ];

  const handleResourceClick = (resource) => {
    if (resource.internal) {
      navigate(resource.url);
    } else {
      window.open(resource.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="min-h-screen bg-white p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#1A3A37] mb-2">
            Your Progress
          </h1>
          <p className="text-gray-600">
            Track your mental wellness journey and discover personalized
            recommendations
            {journals.length > 0 && (
              <span className="text-teal-600 font-medium">
                {" "}
                • {journals.length} journal entries analyzed
              </span>
            )}
          </p>
        </div>

        {/* Progress Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Depression Progress */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-blue-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <Brain className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {depressionImprovement >= 0 ? `${depressionImprovement}%` : `${Math.abs(depressionImprovement)}%`}
            </h3>
            <p className="text-gray-600 text-sm font-medium">
              Depression {depressionImprovement >= 0 ? "Improvement" : "Change"}
            </p>
            <div className="flex items-center justify-center gap-1 mt-1">
              {React.createElement(depressionFeedback.icon, { 
                className: `w-4 h-4 ${depressionFeedback.color}` 
              })}
              <p className={`text-xs ${depressionFeedback.color}`}>
                {depressionFeedback.message}
              </p>
            </div>
          </div>

          {/* Stress Progress */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-orange-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <Heart className="w-6 h-6 text-orange-500" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {stressImprovement >= 0 ? `${stressImprovement}%` : `${Math.abs(stressImprovement)}%`}
            </h3>
            <p className="text-gray-600 text-sm font-medium">
              Stress {stressImprovement >= 0 ? "Reduction" : "Change"}
            </p>
            <div className="flex items-center justify-center gap-1 mt-1">
              {React.createElement(stressFeedback.icon, { 
                className: `w-4 h-4 ${stressFeedback.color}` 
              })}
              <p className={`text-xs ${stressFeedback.color}`}>
                {stressFeedback.message}
              </p>
            </div>
          </div>

          {/* Anxiety Progress */}
          <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm text-center">
            <div className="bg-purple-50 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
              <Shield className="w-6 h-6 text-purple-600" />
            </div>
            <h3 className="text-2xl font-bold text-[#1A3A37]">
              {anxietyImprovement >= 0 ? `${anxietyImprovement}%` : `${Math.abs(anxietyImprovement)}%`}
            </h3>
            <p className="text-gray-600 text-sm font-medium">
              Anxiety {anxietyImprovement >= 0 ? "Reduction" : "Change"}
            </p>
            <div className="flex items-center justify-center gap-1 mt-1">
              {React.createElement(anxietyFeedback.icon, { 
                className: `w-4 h-4 ${anxietyFeedback.color}` 
              })}
              <p className={`text-xs ${anxietyFeedback.color}`}>
                {anxietyFeedback.message}
              </p>
            </div>
          </div>
        </div>

        {/* Progress Chart */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-green-50 p-3 rounded-xl">
              <Activity className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#1A3A37]">
                {progressData.length}-Day Progress Overview
              </h2>
              <p className="text-gray-600 text-sm">
                Track your mental wellness scores over time (Scale: 1-10, lower
                is better)
                {journals.length === 0 && (
                  <span className="text-orange-600 ml-2">
                    • Sample data shown (start journaling to see your real
                    progress)
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="h-96 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={progressData}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: 20,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" stroke="#666" fontSize={12} />
                <YAxis stroke="#666" fontSize={12} domain={[0, 10]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="depression"
                  stroke="#3b82f6"
                  strokeWidth={3}
                  dot={{ fill: "#3b82f6", strokeWidth: 2, r: 4 }}
                  name="Depression"
                />
                <Line
                  type="monotone"
                  dataKey="stress"
                  stroke="#f59e0b"
                  strokeWidth={3}
                  dot={{ fill: "#f59e0b", strokeWidth: 2, r: 4 }}
                  name="Stress"
                />
                <Line
                  type="monotone"
                  dataKey="anxiety"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  dot={{ fill: "#8b5cf6", strokeWidth: 2, r: 4 }}
                  name="Anxiety"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Personalized Recommendations */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="bg-purple-50 p-3 rounded-xl">
              <Lightbulb className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[#1A3A37]">
                Personalized Recommendations
              </h2>
              <p className="text-gray-600 text-sm">
                Based on your progress and current needs
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Recommended Activities */}
            <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-blue-50 p-3 rounded-xl">
                  <Target className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#1A3A37]">
                    Recommended Activities
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Personalized for your progress
                  </p>
                </div>
              </div>
              <div className="space-y-4">
                {recommendedActivities.map((activity, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleResourceClick(activity)}
                    className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`${activity.iconBg} p-2 rounded-lg shrink-0`}>
                        {React.createElement(activity.icon, {
                          className: `w-4 h-4 ${activity.iconColor}`
                        })}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-1 group-hover:text-teal-600 transition-colors">
                          {activity.title}
                        </h4>
                        <p className="text-sm text-gray-600 mb-2">
                          {activity.description}
                        </p>
                        <div className="flex items-center text-xs text-gray-500">
                          <span>{activity.duration}</span>
                          <span className="mx-2">•</span>
                          <span className="text-green-600">{activity.effectiveness}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Learning Resources */}
            <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-green-50 p-3 rounded-xl">
                  <BookOpen className="w-6 h-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#1A3A37]">
                    Learning Resources
                  </h3>
                  <p className="text-gray-600 text-sm">Expand your knowledge</p>
                </div>
              </div>
              <div className="space-y-4">
                {learningResources.map((resource, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleResourceClick(resource)}
                    className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`${resource.iconBg} p-2 rounded-lg shrink-0`}>
                        {React.createElement(resource.icon, {
                          className: `w-4 h-4 ${resource.iconColor}`
                        })}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-1 group-hover:text-teal-600 transition-colors">
                          {resource.title}
                        </h4>
                        <p className="text-sm text-gray-600 mb-2">
                          {resource.description}
                        </p>
                        <div className="flex items-center text-xs text-gray-500">
                          <span>{resource.progress}</span>
                          <span className="mx-2">•</span>
                          <span className="text-blue-600">{resource.status}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Personal Insights */}
            <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-orange-50 p-3 rounded-xl">
                  <User className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-[#1A3A37]">
                    Personal Insights
                  </h3>
                  <p className="text-gray-600 text-sm">
                    Based on your patterns
                  </p>
                </div>
              </div>
              <div className="space-y-4">
                {personalInsights.map((insight, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleResourceClick(insight)}
                    className="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`${insight.iconBg} p-2 rounded-lg shrink-0`}>
                        {React.createElement(insight.icon, {
                          className: `w-4 h-4 ${insight.iconColor}`
                        })}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 mb-1 group-hover:text-teal-600 transition-colors">
                          {insight.title}
                        </h4>
                        <p className="text-sm text-gray-600 mb-2">
                          {insight.description}
                        </p>
                        <div className="flex items-center text-xs text-gray-500">
                          <span>{insight.detail}</span>
                          <span className="mx-2">•</span>
                          <span className={
                            insight.status.includes('better') || insight.status.includes('data')
                              ? 'text-green-600'
                              : insight.status.includes('impact')
                              ? 'text-purple-600'
                              : 'text-blue-600'
                          }>
                            {insight.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mental Health Alert Dialog */}
      {showAlertDialog && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full">
            {/* Header */}
            <div className="bg-rose-500 p-6 text-white flex items-center justify-between rounded-t-3xl">
              <div className="flex items-center gap-3">
                <div className="bg-white/20 p-3 rounded-full">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold">{alertMessage.title}</h3>
                  <p className="text-rose-100 text-sm">Let's prioritize your wellbeing</p>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-8">
              <p className="text-gray-700 text-base mb-6 leading-relaxed">
                {alertMessage.description}
              </p>

              {/* High Parameters Display */}
              {alertMessage.highParameters.length > 0 && (
                <div className="bg-rose-50 rounded-xl p-4 mb-6">
                  <p className="text-sm font-semibold text-rose-800 mb-2">
                    Elevated Metrics:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {alertMessage.highParameters.map((param, idx) => (
                      <span
                        key={idx}
                        className="bg-rose-100 text-rose-700 px-3 py-1 rounded-full text-sm font-medium"
                      >
                        {param}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendation */}
              <div className="bg-teal-50 rounded-xl p-4 mb-6">
                <div className="flex items-start gap-3">
                  <div className="bg-teal-100 p-2 rounded-lg shrink-0">
                    <Heart className="w-5 h-5 text-teal-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-teal-900 mb-1">
                      Recommended Action
                    </h4>
                    <p className="text-sm text-teal-800">
                      Try guided meditation or breathing exercises to help manage your stress and emotions.
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={() => {
                    setShowAlertDialog(false);
                    navigate("/calming");
                  }}
                  className="flex-1 bg-teal-600 text-white px-6 py-3 rounded-full font-semibold hover:bg-teal-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Heart className="w-5 h-5" />
                  Try Meditation
                </button>
                <button
                  onClick={() => {
                    localStorage.setItem("mentalHealthAlertDismissed", "true");
                    setShowAlertDialog(false);
                  }}
                  className="flex-1 border-2 border-gray-300 text-gray-700 px-6 py-3 rounded-full font-semibold hover:bg-gray-50 transition-colors"
                >
                  Not Now
                </button>
              </div>

              {/* Dismissal Note */}
              <p className="text-xs text-gray-500 text-center mt-4">
                Clicking "Not Now" will hide this alert permanently
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

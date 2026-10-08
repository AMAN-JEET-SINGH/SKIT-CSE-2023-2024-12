import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { toast } from "react-toastify";
import {
  User,
  Mail,
  Phone,
  Calendar,
  Heart,
  AlertCircle,
  Edit3,
  Save,
  Lock,
  Key,
  Trash,
  Award,
  Trophy,
  Star,
} from "lucide-react";
import awardSvg from "../assets/award.svg";
import trophySvg from "../assets/TropyStar.svg";
import award2Svg from "../assets/Award2.svg";
;
export default function Profile() {
  const { user, token, getAuthHeaders } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    full_name: user?.full_name || "",
    email: user?.email || "",
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // TODO: Implement profile update API endpoint
      // const response = await fetch('http://localhost:8000/api/auth/update-profile', {
      //   method: 'PUT',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     ...getAuthHeaders()
      //   },
      //   body: JSON.stringify(formData)
      // });

      // For now, just show success message
      toast.success("Profile updated successfully!");
      setIsEditing(false);

      // Update local storage
      const updatedUser = { ...user, ...formData };
      localStorage.setItem("user", JSON.stringify(updatedUser));
    } catch (error) {
      console.error("Profile update error:", error);
      toast.error("Failed to update profile");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      full_name: user?.full_name || "",
      email: user?.email || "",
    });
    setIsEditing(false);
  };

  // Get initials for avatar
  const getInitials = (name) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((word) => word[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="h-full overflow-auto bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="px-6 py-4">
          <h2 className="text-xl font-semibold text-gray-900">
            Profile Settings
          </h2>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6 max-w-4xl mx-auto">
        {/* Profile Card */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          {/* Header Section with Avatar */}
          <div className="bg-gradient-to-r from-stone-900 to-teal-900 px-8 py-12">
            <div className="flex items-center">
              <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center shadow-lg">
                <span className="text-3xl font-bold text-teal-600">
                  {getInitials(user?.full_name)}
                </span>
              </div>
              <div className="ml-6 text-white">
                <h3 className="text-2xl font-bold mb-1">
                  {user?.full_name || "User"}
                </h3>
                <p className="text-teal-100">
                  {user?.email || "user@example.com"}
                </p>
                <p className="text-sm text-teal-100 mt-2">
                  Member since {formatDate(user?.date_created)}
                </p>
              </div>
            </div>
          </div>

          {/* Form Section */}
          <div className="px-8 py-6">
            <form onSubmit={handleSubmit}>
              {/* Personal Information */}
              <div className="mb-8">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-lg font-semibold text-gray-900">
                    Personal Information
                  </h4>
                  {!isEditing && (
                    <button
                      type="button"
                      onClick={() => setIsEditing(true)}
                      className="text-teal-600 hover:text-teal-700 font-medium text-sm flex items-center"
                    >
                      <svg
                        className="w-4 h-4 mr-1"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                        />
                      </svg>
                      Edit Profile
                    </button>
                  )}
                </div>

                <div className="space-y-4">
                  {/* Full Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Full Name
                    </label>
                    {isEditing ? (
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                        required
                      />
                    ) : (
                      <p className="px-4 py-3 bg-gray-50 rounded-lg text-gray-900">
                        {user?.full_name || "Not set"}
                      </p>
                    )}
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email Address
                    </label>
                    {isEditing ? (
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleInputChange}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                        required
                      />
                    ) : (
                      <p className="px-4 py-3 bg-gray-50 rounded-lg text-gray-900">
                        {user?.email || "Not set"}
                      </p>
                    )}
                  </div>

                  {/* Account Status */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Account Status
                    </label>
                    <div className="flex items-center">
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          user?.is_active
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {user?.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                  </div>

                  {/* User ID */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      User ID
                    </label>
                    <p className="px-4 py-3 bg-gray-50 rounded-lg text-gray-600 font-mono text-sm">
                      {user?.id || "N/A"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              {isEditing && (
                <div className="flex justify-end space-x-3 pt-6 border-t border-gray-200">
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                    disabled={isLoading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={isLoading}
                  >
                    {isLoading ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Achievements Card */}
        <div className="bg-white rounded-xl shadow-lg p-8 mt-6">
          <div className="flex items-center justify-between mb-6">
            <h4 className="text-lg font-semibold text-gray-900 flex items-center">
              <Trophy className="w-5 h-5 mr-2 text-teal-600" />
              Achievements
            </h4>
            <span className="text-sm text-gray-500">
              Your wellness journey milestones
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {/* Achievement 1 */}
            <div className="flex flex-col items-center text-center p-4 rounded-lg bg-gradient-to-br from-teal-50 to-blue-50 hover:shadow-md transition-shadow">
              <img 
                src={award2Svg} 
                alt="Award" 
                className="w-16 h-16 mb-3"
              />
              <h5 className="font-semibold text-gray-800 text-sm mb-1">
                First Journal
              </h5>
              <p className="text-xs text-gray-600">
                Started your journey
              </p>
            </div>

            {/* Achievement 2 */}
            <div className="flex flex-col items-center text-center p-4 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 hover:shadow-md transition-shadow">
              <img 
                src={awardSvg} 
                alt="Award" 
                className="w-16 h-16 mb-3"
              />
              <h5 className="font-semibold text-gray-800 text-sm mb-1">
                3-Day Streak
              </h5>
              <p className="text-xs text-gray-600">
                Consistency champion
              </p>
            </div>

            {/* Achievement 3 */}
            <div className="flex flex-col items-center text-center p-4 rounded-lg bg-gradient-to-br from-purple-50 to-pink-50 hover:shadow-md transition-shadow">
              <img 
                src={trophySvg} 
                alt="Award" 
                className="w-16 h-16 mb-3"
              />
              <h5 className="font-semibold text-gray-800 text-sm mb-1">
                5 Journals
              </h5>
              <p className="text-xs text-gray-600">
                Dedicated writer
              </p>
            </div>
          </div>
        </div>

        {/* Additional Settings Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* Security Settings */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <svg
                className="w-5 h-5 mr-2 text-teal-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              Security
            </h4>
            <button className="w-full text-left px-4 py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Change Password</span>
                <svg
                  className="w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </button>
          </div>

          {/* Privacy Settings */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <svg
                className="w-5 h-5 mr-2 text-teal-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              Privacy
            </h4>
            <button className="w-full text-left px-4 py-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
              <div className="flex justify-between items-center">
                <span className="text-gray-700">Privacy Settings</span>
                <svg
                  className="w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl shadow-lg p-6 mt-6 border-2 border-red-200">
          <h4 className="text-lg font-semibold text-red-600 mb-4 flex items-center">
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            Danger Zone
          </h4>
          <p className="text-gray-600 mb-4">
            Once you delete your account, there is no going back. Please be
            certain.
          </p>
          <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium transition-colors">
            Delete Account
          </button>
        </div>
      </main>
    </div>
  );
}

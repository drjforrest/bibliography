"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import axios from "axios";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface UserProfile {
  id: string;
  email: string;
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  openrouter_api_key_set: boolean;
}

export default function ProfilePage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [elevenlabsKey, setElevenlabsKey] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchProfile = useCallback(async () => {
    const token = await getToken({ template: "hero-library-jwt" });
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/v1/profile`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setProfile(response.data);
      setDisplayName(response.data.display_name || "");
      setBio(response.data.bio || "");
    } catch (error) {
      console.error("Failed to fetch profile:", error);
      showMessage("error", "Failed to load profile");
    } finally {
      setIsLoading(false);
    }
  }, [getToken, API_URL]);

  useEffect(() => {
    // Wait for Clerk to finish loading. If loaded and not signed in,
    // redirect to the sign-in page. Only fetch the profile when
    // auth is loaded and the user is signed in.
    if (!isLoaded) return;

    if (isLoaded && !isSignedIn) {
      // perform a client-side redirect to sign-in
      router.push("/sign-in");
      return;
    }

    if (isSignedIn) {
      fetchProfile();
    }
  }, [isLoaded, isSignedIn, router, fetchProfile]);

  // Track unsaved changes
  useEffect(() => {
    const originalDisplayName = profile?.display_name || "";
    const originalBio = profile?.bio || "";
    setHasUnsavedChanges(displayName !== originalDisplayName || bio !== originalBio || !!avatarFile || !!openrouterKey.trim() || !!openaiKey.trim() || !!elevenlabsKey.trim());
  }, [displayName, bio, avatarFile, openrouterKey, profile]);

  const showMessage = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const uploadAvatar = async () => {
    const token = await getToken({ template: "hero-library-jwt" });
    if (!token || !avatarFile) return;

    const formData = new FormData();
    formData.append("file", avatarFile);

    try {
      const response = await axios.post(`${API_URL}/api/v1/profile/avatar`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });
      setProfile((prev) => prev ? { ...prev, avatar_url: response.data.avatar_url } : null);
      setAvatarFile(null);
      setAvatarPreview(null);
      showMessage("success", "Avatar uploaded successfully");
    } catch (error) {
      console.error("Failed to upload avatar:", error);
      showMessage("error", "Failed to upload avatar");
    }
  };

  const deleteAvatar = async () => {
    const token = await getToken({ template: "hero-library-jwt" });
    if (!token || !confirm("Are you sure you want to delete your avatar?")) return;

    try {
      await axios.delete(`${API_URL}/api/v1/profile/avatar`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setProfile((prev) => prev ? { ...prev, avatar_url: undefined } : null);
      showMessage("success", "Avatar deleted successfully");
    } catch (error) {
      console.error("Failed to delete avatar:", error);
      showMessage("error", "Failed to delete avatar");
    }
  };

  const handleSaveProfile = async () => {
    const token = await getToken({ template: "hero-library-jwt" });
    if (!token) return;

    setIsSaving(true);
    try {
      // Save profile info
      const profileResponse = await axios.put(
        `${API_URL}/api/v1/profile`,
        {
          display_name: displayName.trim() || null,
          bio: bio.trim() || null,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      setProfile(profileResponse.data);

      // Upload avatar if selected
      if (avatarFile) {
        await uploadAvatar();
      }

      // Save API keys if any were provided
      const apiKeysData: any = {};
      if (openrouterKey.trim()) apiKeysData.openrouter_api_key = openrouterKey.trim();
      if (openaiKey.trim()) apiKeysData.openai_api_key = openaiKey.trim();
      if (elevenlabsKey.trim()) apiKeysData.elevenlabs_api_key = elevenlabsKey.trim();
      
      if (Object.keys(apiKeysData).length > 0) {
        await axios.put(
          `${API_URL}/api/v1/api-keys`,
          apiKeysData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        setOpenrouterKey("");
        setOpenaiKey("");
        setElevenlabsKey("");
      }

      showMessage("success", "Profile updated successfully");
      // Navigate back after successful save
      setTimeout(() => router.back(), 1500);
    } catch (error) {
      console.error("Failed to save profile:", error);
      showMessage("error", "Failed to save profile");
    } finally {
      setIsSaving(false);
    }
  };

  const getAvatarUrl = () => {
    if (avatarPreview) return avatarPreview;
    if (profile?.avatar_url) return `${API_URL}${profile.avatar_url}`;
    return `https://ui-avatars.com/api/?name=${encodeURIComponent(displayName || profile?.email || "User")}`;
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Checking authentication...</div>
      </div>
    );
  }

  if (isLoaded && !isSignedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Redirecting to sign-in...</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-600 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  const handleCancel = () => {
    if (hasUnsavedChanges && !confirm("You have unsaved changes. Are you sure you want to leave?")) {
      return;
    }
    router.back();
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Profile Settings</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your profile information, avatar, and API keys
          </p>
        </div>
        <button
          onClick={handleCancel}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title="Close"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg ${
            message.type === "success"
              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
              : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 space-y-6">
        {/* Avatar Section */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Avatar</h2>
          <div className="flex items-center gap-6">
            <div className="relative">
              <img
                src={getAvatarUrl()}
                alt="Avatar"
                className="w-24 h-24 rounded-full object-cover border-4 border-gray-200 dark:border-gray-700"
              />
            </div>
            <div className="flex-1">
              <input
                type="file"
                accept="image/*"
                onChange={handleAvatarChange}
                className="hidden"
                id="avatar-upload"
              />
              <div className="flex gap-3">
                <label
                  htmlFor="avatar-upload"
                  className="px-4 py-2 bg-[#4e989e] hover:bg-[#3d7a7f] text-white rounded-lg cursor-pointer transition-colors"
                >
                  Choose Image
                </label>
                {profile?.avatar_url && (
                  <button
                    onClick={deleteAvatar}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    Delete Avatar
                  </button>
                )}
              </div>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                JPG, PNG, GIF or WebP. Max size 5MB.
              </p>
            </div>
          </div>
        </div>

        {/* Profile Information */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            Profile Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email
              </label>
              <input
                type="email"
                value={profile?.email || ""}
                disabled
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Your name"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#4e989e]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Bio
              </label>
              <textarea
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="Tell us about yourself..."
                rows={4}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#4e989e]"
              />
            </div>
          </div>
        </div>

        {/* API Keys Section */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            API Keys
          </h2>
          <div className="space-y-4">
            {/* OpenRouter Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                OpenRouter API Key <span className="text-xs text-gray-500 dark:text-gray-400">(LLM)</span>
                {profile && (
                  <span
                    className={`ml-2 text-xs px-2 py-1 rounded ${
                      profile.openrouter_api_key_set
                        ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                        : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                    }`}
                  >
                    {profile.openrouter_api_key_set ? "Set" : "Not Set"}
                  </span>
                )}
              </label>
              <input
                type="password"
                value={openrouterKey}
                onChange={(e) => setOpenrouterKey(e.target.value)}
                placeholder="sk-or-v1-..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#4e989e]"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                For podcast script generation (access to 100+ AI models)
              </p>
            </div>

            {/* OpenAI Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                OpenAI API Key <span className="text-xs text-gray-500 dark:text-gray-400">(TTS)</span>
              </label>
              <input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#4e989e]"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                For podcast TTS generation (pay-per-use, $15/1M chars)
              </p>
            </div>

            {/* ElevenLabs Key */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                ElevenLabs API Key <span className="text-xs text-gray-500 dark:text-gray-400">(TTS)</span>
              </label>
              <input
                type="password"
                value={elevenlabsKey}
                onChange={(e) => setElevenlabsKey(e.target.value)}
                placeholder="..."
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-[#4e989e]"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                For podcast TTS generation (subscription-based, $5-99/month)
              </p>
            </div>

            <div className="bg-[#4e989e]/10 dark:bg-[#4e989e]/20 border border-[#4e989e]/30 dark:border-[#4e989e]/40 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="material-symbols-outlined text-[#4e989e] dark:text-[#94d2bd] mt-0.5">
                  info
                </span>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                    Why OpenRouter?
                  </h3>
                  <p className="text-sm text-gray-800 dark:text-gray-200 mb-2">
                    OpenRouter gives you access to 100+ AI models through a single API key, including:
                  </p>
                  <ul className="text-sm text-gray-800 dark:text-gray-200 list-disc list-inside space-y-1">
                    <li>GPT-4, GPT-4 Turbo, GPT-3.5 (OpenAI)</li>
                    <li>Claude 3 Opus, Sonnet, Haiku (Anthropic)</li>
                    <li>Gemini Pro (Google)</li>
                    <li>Llama 3, Mixtral, and many more open-source models</li>
                  </ul>
                  <p className="text-sm text-gray-800 dark:text-gray-200 mt-3">
                    Get your API key at{" "}
                    <a
                      href="https://openrouter.ai"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline font-medium hover:text-[#3d7a7f] dark:hover:text-[#94d2bd]"
                    >
                      openrouter.ai
                    </a>
                  </p>
                </div>
              </div>
            </div>

            <p className="text-sm text-gray-500 dark:text-gray-400">
              Your API keys are stored securely and used for AI-powered features like podcast generation.
              They enable you to use your own provider accounts instead of relying on system defaults.
            </p>
          </div>
        </div>

        {/* Save/Cancel Buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleCancel}
            disabled={isSaving}
            className="px-6 py-3 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-200 text-gray-700 disabled:text-gray-500 rounded-lg transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleSaveProfile}
            disabled={isSaving}
            className="px-6 py-3 bg-[#4e989e] hover:bg-[#3d7a7f] disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}

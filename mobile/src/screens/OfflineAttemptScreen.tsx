/**Offline attempt screen for answering questions offline.*/

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from "react-native";
import { TestPackageOut, QuestionSnapshot } from "../types/api";
import { getLocalPackage, listPackages } from "../offline/packageManager";
import { enqueueAttemptItem } from "../offline/attemptQueue";
import { generateUUID } from "../utils/uuid";

interface OfflineAttemptScreenProps {
  onBack: () => void;
}

export function OfflineAttemptScreen({ onBack }: OfflineAttemptScreenProps) {
  const [packages, setPackages] = useState<{ package_id: string; name: string }[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);
  const [packageData, setPackageData] = useState<TestPackageOut | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPackages();
  }, []);

  const loadPackages = async () => {
    try {
      setLoading(true);
      const items = await listPackages();
      setPackages(
        items.map((p) => ({ package_id: p.package_id, name: p.name }))
      );
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to load packages");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPackage = async (packageId: string) => {
    try {
      setLoading(true);
      const data = await getLocalPackage(packageId);
      if (data) {
        setPackageData(data);
        setSelectedPackageId(packageId);
        setAnswers({});
      } else {
        Alert.alert("Error", "Package not downloaded. Please download first.");
      }
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to load package");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = (questionId: string, optionIndex: number) => {
    setAnswers({ ...answers, [questionId]: optionIndex });
  };

  const handleSaveOffline = async () => {
    if (!selectedPackageId || !packageData) {
      Alert.alert("Error", "No package selected");
      return;
    }

    const answeredQuestions = Object.keys(answers);
    if (answeredQuestions.length === 0) {
      Alert.alert("Info", "No questions answered");
      return;
    }

    try {
      setSaving(true);
      const offlineSessionId = generateUUID();
      const now = new Date().toISOString();

      // Enqueue each answered question as a separate attempt
      for (const questionId of answeredQuestions) {
        await enqueueAttemptItem(
          selectedPackageId,
          offlineSessionId,
          questionId,
          answers[questionId],
          now
        );
      }

      Alert.alert("Success", `Saved ${answeredQuestions.length} attempt(s) to queue`);
      setAnswers({});
    } catch (error: any) {
      Alert.alert("Error", error.message || "Failed to save attempts");
    } finally {
      setSaving(false);
    }
  };

  const renderQuestion = (question: QuestionSnapshot, index: number) => {
    const questionId = question.question_id;
    const selected = answers[questionId];

    return (
      <View key={questionId} style={styles.questionCard}>
        <Text style={styles.questionNumber}>Question {index + 1}</Text>
        <Text style={styles.questionStem}>{question.stem}</Text>

        {[
          { label: "A", value: question.option_a, index: 0 },
          { label: "B", value: question.option_b, index: 1 },
          { label: "C", value: question.option_c, index: 2 },
          { label: "D", value: question.option_d, index: 3 },
          { label: "E", value: question.option_e, index: 4 },
        ]
          .filter((opt) => opt.value)
          .map((opt) => (
            <TouchableOpacity
              key={opt.index}
              style={[
                styles.option,
                selected === opt.index && styles.optionSelected,
              ]}
              onPress={() => handleAnswer(questionId, opt.index)}
            >
              <Text style={styles.optionLabel}>{opt.label}.</Text>
              <Text style={styles.optionText}>{opt.value}</Text>
            </TouchableOpacity>
          ))}
      </View>
    );
  };

  if (loading && !packageData) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!selectedPackageId) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onBack}>
            <Text style={styles.backButton}>← Back</Text>
          </TouchableOpacity>
          <Text style={styles.title}>Select Package</Text>
        </View>

        <ScrollView style={styles.list}>
          {packages.map((pkg) => (
            <TouchableOpacity
              key={pkg.package_id}
              style={styles.packageItem}
              onPress={() => handleSelectPackage(pkg.package_id)}
            >
              <Text style={styles.packageName}>{pkg.name}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>
    );
  }

  // Show first 5 questions only (minimal demo)
  const questionsToShow = packageData.questions.slice(0, 5);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => setSelectedPackageId(null)}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>{packageData.name}</Text>
        <Text style={styles.subtitle}>
          {questionsToShow.length} questions (showing first 5)
        </Text>
      </View>

      <ScrollView style={styles.content}>
        {questionsToShow.map((q, i) => renderQuestion(q, i))}
      </ScrollView>

      <View style={styles.footer}>
        <Text style={styles.answeredCount}>
          Answered: {Object.keys(answers).length} / {questionsToShow.length}
        </Text>
        <TouchableOpacity
          style={[styles.saveButton, saving && styles.saveButtonDisabled]}
          onPress={handleSaveOffline}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.saveButtonText}>Save Offline Attempt</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f5f5f5",
  },
  header: {
    padding: 20,
    backgroundColor: "#fff",
    borderBottomWidth: 1,
    borderBottomColor: "#ddd",
  },
  backButton: {
    fontSize: 16,
    color: "#1976d2",
    marginBottom: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: "#666",
  },
  list: {
    flex: 1,
  },
  packageItem: {
    backgroundColor: "#fff",
    padding: 16,
    margin: 8,
    marginHorizontal: 16,
    borderRadius: 8,
  },
  packageName: {
    fontSize: 16,
    fontWeight: "600",
  },
  content: {
    flex: 1,
  },
  questionCard: {
    backgroundColor: "#fff",
    padding: 16,
    margin: 8,
    marginHorizontal: 16,
    borderRadius: 8,
    marginTop: 16,
  },
  questionNumber: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1976d2",
    marginBottom: 8,
  },
  questionStem: {
    fontSize: 16,
    marginBottom: 16,
    lineHeight: 24,
  },
  option: {
    flexDirection: "row",
    padding: 12,
    marginBottom: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#ddd",
    backgroundColor: "#fafafa",
  },
  optionSelected: {
    borderColor: "#1976d2",
    backgroundColor: "#e3f2fd",
  },
  optionLabel: {
    fontSize: 16,
    fontWeight: "600",
    marginRight: 8,
    minWidth: 24,
  },
  optionText: {
    fontSize: 16,
    flex: 1,
  },
  footer: {
    padding: 16,
    backgroundColor: "#fff",
    borderTopWidth: 1,
    borderTopColor: "#ddd",
  },
  answeredCount: {
    fontSize: 14,
    marginBottom: 12,
    textAlign: "center",
    color: "#666",
  },
  saveButton: {
    backgroundColor: "#4caf50",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  saveButtonDisabled: {
    opacity: 0.6,
  },
  saveButtonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});

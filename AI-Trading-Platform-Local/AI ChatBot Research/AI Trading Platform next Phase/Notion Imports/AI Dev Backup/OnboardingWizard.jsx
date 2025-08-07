import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  ChevronLeft, 
  ChevronRight, 
  Brain, 
  TrendingUp, 
  Shield, 
  Target,
  Monitor,
  Zap,
  CheckCircle,
  ArrowRight
} from 'lucide-react';
import WelcomeStep from './steps/WelcomeStep';
import ExperienceStep from './steps/ExperienceStep';
import RiskToleranceStep from './steps/RiskToleranceStep';
import InvestmentGoalsStep from './steps/InvestmentGoalsStep';
import TradingStyleStep from './steps/TradingStyleStep';
import PlatformPreferencesStep from './steps/PlatformPreferencesStep';
import StrategySelectionStep from './steps/StrategySelectionStep';
import CustomizationStep from './steps/CustomizationStep';
import ReviewStep from './steps/ReviewStep';
import CompletionStep from './steps/CompletionStep';
import './OnboardingWizard.css';

const OnboardingWizard = ({ userId, onComplete }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [sessionId, setSessionId] = useState(null);
  const [sessionData, setSessionData] = useState(null);
  const [responses, setResponses] = useState({});
  const [aiInsights, setAiInsights] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Step configuration
  const steps = [
    {
      id: 'welcome',
      title: 'Welcome',
      description: 'Get started with AI-powered trading',
      icon: Brain,
      component: WelcomeStep
    },
    {
      id: 'experience',
      title: 'Experience',
      description: 'Tell us about your trading background',
      icon: TrendingUp,
      component: ExperienceStep
    },
    {
      id: 'risk_tolerance',
      title: 'Risk Tolerance',
      description: 'Define your comfort with risk',
      icon: Shield,
      component: RiskToleranceStep
    },
    {
      id: 'investment_goals',
      title: 'Investment Goals',
      description: 'What do you want to achieve?',
      icon: Target,
      component: InvestmentGoalsStep
    },
    {
      id: 'trading_style',
      title: 'Trading Style',
      description: 'Choose your preferred approach',
      icon: Zap,
      component: TradingStyleStep
    },
    {
      id: 'platform_preferences',
      title: 'Platforms',
      description: 'Select your trading platforms',
      icon: Monitor,
      component: PlatformPreferencesStep
    },
    {
      id: 'strategy_selection',
      title: 'Strategies',
      description: 'Pick your strategy preferences',
      icon: TrendingUp,
      component: StrategySelectionStep
    },
    {
      id: 'customization',
      title: 'Personalization',
      description: 'Customize your AI assistant',
      icon: Brain,
      component: CustomizationStep
    },
    {
      id: 'review',
      title: 'Review',
      description: 'Confirm your configuration',
      icon: CheckCircle,
      component: ReviewStep
    },
    {
      id: 'completion',
      title: 'Complete',
      description: 'Your AI setup is ready!',
      icon: CheckCircle,
      component: CompletionStep
    }
  ];

  // Initialize onboarding session with mock data for demo
  useEffect(() => {
    initializeSession();
  }, [userId]);

  const initializeSession = async () => {
    try {
      setIsLoading(true);
      
      // Mock session initialization for demo purposes
      await new Promise(resolve => setTimeout(resolve, 800)); // Simulate API delay
      
      const mockSessionData = {
        id: `session_${Date.now()}`,
        user_id: userId || 'demo_user',
        status: 'active',
        created_at: new Date().toISOString(),
        config: {
          version: '2.0',
          features: ['ai_analysis', 'strategy_recommendations', 'quantum_security']
        }
      };
      
      setSessionId(mockSessionData.id);
      setSessionData(mockSessionData);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepResponse = async (response) => {
    if (!sessionId) return;

    try {
      setIsLoading(true);
      
      // Mock response processing for demo
      await new Promise(resolve => setTimeout(resolve, 600)); // Simulate API delay
      
      // Update local state
      setResponses(prev => ({
        ...prev,
        [steps[currentStep].id]: response
      }));

      // Generate mock AI insights based on the step
      const mockInsights = generateMockInsights(steps[currentStep].id, response);
      if (mockInsights) {
        setAiInsights(prev => [...prev, {
          step: steps[currentStep].id,
          analysis: mockInsights.analysis,
          recommendations: mockInsights.recommendations || []
        }]);
      }

      // Advance to next step
      await advanceStep();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const generateMockInsights = (stepId, response) => {
    const insights = {
      experience: {
        analysis: "Based on your experience level, I recommend starting with conservative strategies and gradually increasing complexity as you become more comfortable with the platform.",
        recommendations: ["Start with paper trading", "Focus on major currency pairs", "Use lower leverage initially"]
      },
      risk_tolerance: {
        analysis: "Your risk profile suggests a balanced approach between growth and capital preservation. This aligns well with our AI-driven strategies.",
        recommendations: ["Diversified portfolio allocation", "Moderate position sizing", "Stop-loss automation"]
      },
      trading_style: {
        analysis: "Your trading style preferences indicate you'd benefit from our automated AI strategies with customizable parameters.",
        recommendations: ["AI-powered day trading signals", "Quantum-secured execution", "Real-time market analysis"]
      },
      goals: {
        analysis: "Your investment goals align perfectly with our platform's capabilities for both short-term gains and long-term wealth building.",
        recommendations: ["Hybrid strategy approach", "Regular portfolio rebalancing", "Performance tracking dashboard"]
      }
    };
    
    return insights[stepId] || null;
  };

  const advanceStep = async () => {
    if (!sessionId) return;

    try {
      // Mock step advancement
      await new Promise(resolve => setTimeout(resolve, 300));
      
      if (currentStep < steps.length - 1) {
        setCurrentStep(prev => prev + 1);
      } else {
        // Complete onboarding
        await completeOnboarding();
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const completeOnboarding = async () => {
    try {
      // Mock completion process
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const completionData = {
        session_id: sessionId,
        user_profile: responses,
        ai_insights: aiInsights,
        recommended_strategies: [
          "Quantum-Enhanced Momentum Trading",
          "AI Risk-Adjusted Portfolio",
          "Automated Arbitrage Detection"
        ],
        completion_time: new Date().toISOString()
      };
      
      if (onComplete) {
        onComplete(completionData);
      }
    } catch (err) {
      setError(err.message);
    }
  };
  const goBackStep = async () => {
    if (currentStep === 0 || !sessionId) return;

    try {
      // Mock going back a step
      await new Promise(resolve => setTimeout(resolve, 200));
      setCurrentStep(prev => Math.max(prev - 1, 0));
    } catch (err) {
      setError(err.message);
    }
  };

  const progress = ((currentStep + 1) / steps.length) * 100;
  const CurrentStepComponent = steps[currentStep]?.component;
  const currentStepData = steps[currentStep];

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={initializeSession} className="w-full">
              Try Again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                <Brain className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">AI Strategy Onboarding</h1>
                <p className="text-sm text-gray-600">Personalized trading setup in 5 minutes</p>
              </div>
            </div>
            <Badge variant="secondary" className="text-xs">
              Step {currentStep + 1} of {steps.length}
            </Badge>
          </div>
          
          {/* Progress Bar */}
          <div className="mt-4">
            <div className="flex justify-between text-xs text-gray-600 mb-2">
              <span>{currentStepData?.title}</span>
              <span>{Math.round(progress)}% Complete</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="w-full shadow-lg border-0 bg-white/90 backdrop-blur-sm">
              <CardHeader className="text-center pb-6">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  {currentStepData && (
                    <currentStepData.icon className="w-8 h-8 text-white" />
                  )}
                </div>
                <CardTitle className="text-2xl font-bold text-gray-900">
                  {currentStepData?.title}
                </CardTitle>
                <CardDescription className="text-lg text-gray-600">
                  {currentStepData?.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="px-8 pb-8">
                {CurrentStepComponent && (
                  <CurrentStepComponent
                    onResponse={handleStepResponse}
                    responses={responses}
                    aiInsights={aiInsights}
                    isLoading={isLoading}
                    sessionData={sessionData}
                  />
                )}
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex justify-between items-center mt-8">
          <Button
            variant="outline"
            onClick={goBackStep}
            disabled={currentStep === 0 || isLoading}
            className="flex items-center space-x-2"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Back</span>
          </Button>

          <div className="flex space-x-2">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`w-3 h-3 rounded-full transition-colors ${
                  index < currentStep
                    ? 'bg-green-500'
                    : index === currentStep
                    ? 'bg-blue-500'
                    : 'bg-gray-300'
                }`}
              />
            ))}
          </div>

          <div className="w-20" /> {/* Spacer for alignment */}
        </div>

        {/* AI Insights Panel */}
        {aiInsights.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8"
          >
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Brain className="w-5 h-5 text-blue-600" />
                  <span>AI Insights</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {aiInsights.slice(-2).map((insight, index) => (
                    <div key={index} className="bg-white/60 rounded-lg p-4">
                      <p className="text-sm text-gray-700 mb-2">{insight.analysis}</p>
                      {insight.recommendations.length > 0 && (
                        <div className="space-y-1">
                          {insight.recommendations.map((rec, recIndex) => (
                            <div key={recIndex} className="flex items-start space-x-2 text-xs text-blue-700">
                              <ArrowRight className="w-3 h-3 mt-0.5 flex-shrink-0" />
                              <span>{rec}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default OnboardingWizard;


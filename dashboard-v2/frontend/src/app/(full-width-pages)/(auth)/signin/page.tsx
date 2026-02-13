import SignInForm from "@/components/auth/SignInForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign In | TrackBoard",
  description: "Sign in to TrackBoard",
};

export default function SignIn() {
  return <SignInForm />;
}

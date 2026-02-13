import SignUpForm from "@/components/auth/SignUpForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign Up | TrackBoard",
  description: "Sign up for TrackBoard",
};

export default function SignUp() {
  return <SignUpForm />;
}

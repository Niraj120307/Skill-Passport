import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { EmptyState } from "../components/ui";

export default function NotFound() {
  return (
    <EmptyState icon={Compass} title="Page not found" body="That page does not exist." action={<Link to="/" className="btn-primary">Back to dashboard</Link>} />
  );
}

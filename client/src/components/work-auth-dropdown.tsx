import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { workAuthorizationOptions, type WorkAuthorization } from "@shared/schema";

interface WorkAuthDropdownProps {
  value: WorkAuthorization;
  onChange: (value: WorkAuthorization) => void;
}

export default function WorkAuthDropdown({ value, onChange }: WorkAuthDropdownProps) {
  return (
    <div className="space-y-3">
      <Label 
        htmlFor="work-auth"
        className="font-serif text-base font-medium"
      >
        Target Work Authorization
      </Label>
      <Select 
        value={value} 
        onValueChange={(v) => onChange(v as WorkAuthorization)}
      >
        <SelectTrigger 
          id="work-auth"
          className="w-full h-12 border-2 border-foreground rounded-sm focus:ring-0 focus:border-foreground font-serif"
          data-testid="select-work-auth"
        >
          <SelectValue placeholder="Select work authorization" />
        </SelectTrigger>
        <SelectContent>
          {workAuthorizationOptions.map((option) => (
            <SelectItem 
              key={option} 
              value={option}
              className="font-serif py-3"
              data-testid={`option-work-auth-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/, "")}`}
            >
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

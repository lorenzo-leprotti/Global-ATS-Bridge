import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { IndustryTemplate, TemplateOption } from "@shared/schema";

interface TemplateSelectorProps {
  value: IndustryTemplate;
  onChange: (value: IndustryTemplate) => void;
}

export default function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  const { data: templates, isLoading } = useQuery<TemplateOption[]>({
    queryKey: ["/api/templates"],
  });

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
        Industry Template
      </label>
      <Select value={value} onValueChange={(v) => onChange(v as IndustryTemplate)}>
        <SelectTrigger 
          className="w-full border-2 border-foreground/20 rounded-sm"
          data-testid="select-template"
        >
          <SelectValue placeholder={isLoading ? "Loading..." : "Select industry"} />
        </SelectTrigger>
        <SelectContent>
          {templates?.map((template) => (
            <SelectItem 
              key={template.id} 
              value={template.id}
              data-testid={`option-template-${template.id}`}
            >
              <div className="flex flex-col items-start">
                <span className="font-medium">{template.name}</span>
                <span className="text-xs text-muted-foreground">{template.description}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

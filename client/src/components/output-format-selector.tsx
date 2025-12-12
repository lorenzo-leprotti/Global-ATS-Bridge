import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { OutputFormat } from "@shared/schema";

interface OutputFormatSelectorProps {
  value: OutputFormat;
  onChange: (value: OutputFormat) => void;
}

export default function OutputFormatSelector({ value, onChange }: OutputFormatSelectorProps) {
  return (
    <div className="space-y-3">
      <Label className="font-serif text-base font-medium">
        Output Format
      </Label>
      <RadioGroup
        value={value}
        onValueChange={(v) => onChange(v as OutputFormat)}
        className="flex items-center gap-8"
        data-testid="radio-output-format"
      >
        <div className="flex items-center gap-3">
          <RadioGroupItem 
            value="pdf" 
            id="pdf" 
            className="w-6 h-6 border-2 border-foreground"
            data-testid="radio-pdf"
          />
          <Label 
            htmlFor="pdf" 
            className="font-serif text-base cursor-pointer"
          >
            PDF
          </Label>
        </div>
        <div className="flex items-center gap-3">
          <RadioGroupItem 
            value="docx" 
            id="docx" 
            className="w-6 h-6 border-2 border-foreground"
            data-testid="radio-docx"
          />
          <Label 
            htmlFor="docx" 
            className="font-serif text-base cursor-pointer"
          >
            DOCX
          </Label>
        </div>
      </RadioGroup>
    </div>
  );
}

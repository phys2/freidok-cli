# Publications
{% for pub in publications %}
   {% set comma = joiner(", ") %}
   {% set authors %} 
   {%- for author in pub.persons -%}
     {{ comma() }}{{ author.forename }} {{ author.surname }}
   {%-  endfor -%}
   {% endset %}  
-  {{ authors  | wordwrap(break_long_words=false, break_on_hyphens=false, wrapstring='\n   ') }}

   {{ pub.titles[0].value | wordwrap(break_long_words=false, break_on_hyphens=false, wrapstring='\n   ') }}

   {% set source = pub.source_journal[0] %}
   {{ source.title }} 
   {%- if source.volume %} {{ source.volume }} {% endif %}
   {%- if source.year %}({{ source.year }}) {% endif %}
   {%- if source.issue %}{{ source.issue }}, {% endif %}
   {%- if source.page %}{{ source.page }}{% endif %}  
   {%+ if pub.pub_ids %}{{ pub.pub_ids[0].link }}{% endif %}

{% endfor %}

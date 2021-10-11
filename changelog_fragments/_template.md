{{ versiondata.name }} {{ versiondata.version }} ({{ versiondata.date }})
{{ top_underline * ((versiondata.name + versiondata.version + versiondata.date)|length + 4)}}

{% for section, _ in sections.items() %}
{% set underline = "-" %}{% if section %}{{section}}
{{ underline * section|length }}{% set underline = "~" %}

{% endif %}

{% if sections[section] %}
{% for category, val in definitions.items() if category in sections[section]%}
{{ definitions[category]['name'] }}
{{ underline * definitions[category]['name']|length }}

{% if definitions[category]['showcontent'] %}
{% for text, values in sections[section][category].items() %}
- {{ text }} ({{ values|join(', ') }})
{% endfor %}

{% else %}
- {{ sections[section][category]['']|join(', ') }}

{% endif %}

{% endfor %}
{% endif %}
{% endfor %}
